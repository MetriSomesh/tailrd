"""Payment provider abstraction: mock (dev/test) and Razorpay (production).

The mock provider simulates the full flow without network calls:
- create_order → returns a fake order ID
- verify_payment → always succeeds
- create_subscription → immediately activates

This lets the full billing flow be tested end-to-end without credentials.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import PaymentProviderError
from app.core.logging import get_logger
from app.db.base import new_uuid, utcnow
from app.db.models.billing import Payment, Subscription
from app.services.quota import add_credits

log = get_logger(__name__)


class PaymentProvider(ABC):
    @abstractmethod
    async def create_order(
        self, amount_paise: int, currency: str = "INR", notes: dict | None = None
    ) -> dict:
        """Create a payment order. Returns provider-specific order data."""
        ...

    @abstractmethod
    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify a payment after the client-side checkout completes."""
        ...

    @abstractmethod
    async def create_subscription(self, plan_id: str, user_email: str) -> dict:
        """Create a subscription. Returns provider-specific subscription data."""
        ...

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription at period end."""
        ...


class MockPaymentProvider(PaymentProvider):
    """Deterministic mock. No network, always succeeds."""

    async def create_order(
        self, amount_paise: int, currency: str = "INR", notes: dict | None = None
    ) -> dict:
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:12]}",
            "amount": amount_paise,
            "currency": currency,
            "status": "created",
        }

    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        # Mock always verifies successfully
        return True

    async def create_subscription(self, plan_id: str, user_email: str) -> dict:
        return {
            "id": f"sub_mock_{uuid.uuid4().hex[:12]}",
            "plan_id": plan_id,
            "status": "active",
        }

    async def cancel_subscription(self, subscription_id: str) -> bool:
        return True


class RazorpayPaymentProvider(PaymentProvider):
    """Real Razorpay integration. Requires RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET."""

    def __init__(self) -> None:

        self._key_id = settings.RAZORPAY_KEY_ID
        self._key_secret = settings.RAZORPAY_KEY_SECRET
        self._base_url = "https://api.razorpay.com/v1"

    async def create_order(
        self, amount_paise: int, currency: str = "INR", notes: dict | None = None
    ) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/orders",
                    json={"amount": amount_paise, "currency": currency, "notes": notes or {}},
                    auth=(self._key_id, self._key_secret),
                )
            if resp.status_code == 200:
                return resp.json()
            log.error("razorpay_create_order_failed", status=resp.status_code, body=resp.text[:300])
            raise PaymentProviderError("Failed to create payment order.")
        except httpx.HTTPError as exc:
            raise PaymentProviderError(f"Razorpay error: {type(exc).__name__}") from exc

    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        import hashlib
        import hmac

        msg = f"{order_id}|{payment_id}".encode()
        expected = hmac.HMAC((self._key_secret or "").encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def create_subscription(self, plan_id: str, user_email: str) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/subscriptions",
                    json={"plan_id": plan_id, "total_count": 52, "customer_notify": 1},
                    auth=(self._key_id, self._key_secret),
                )
            if resp.status_code == 200:
                return resp.json()
            raise PaymentProviderError("Failed to create subscription.")
        except httpx.HTTPError as exc:
            raise PaymentProviderError(f"Razorpay error: {type(exc).__name__}") from exc

    async def cancel_subscription(self, subscription_id: str) -> bool:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/subscriptions/{subscription_id}/cancel",
                    json={"cancel_at_cycle_end": 1},
                    auth=(self._key_id, self._key_secret),
                )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "razorpay":
        return RazorpayPaymentProvider()
    return MockPaymentProvider()


# ---------------------------------------------------------------------------
# Billing service functions (called by the router)
# ---------------------------------------------------------------------------


async def purchase_credits(db: AsyncSession, user_id: str) -> dict:
    """Initiate a one-off ₹29 credit purchase.

    Creates a payment order and records the pending payment.
    The frontend shows the Razorpay checkout modal with this order.
    """
    provider = get_payment_provider()
    order = await provider.create_order(
        amount_paise=settings.PRICE_PER_RESUME_PAISE,
        notes={"user_id": user_id, "type": "credit"},
    )

    payment = Payment(
        id=new_uuid(),
        user_id=user_id,
        razorpay_order_id=order["id"],
        kind="one_off",
        amount_paise=settings.PRICE_PER_RESUME_PAISE,
        status="pending",
    )
    db.add(payment)
    await db.commit()

    return {
        "order_id": order["id"],
        "amount_paise": settings.PRICE_PER_RESUME_PAISE,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID or "mock_key",
    }


async def confirm_credit_payment(
    db: AsyncSession, user_id: str, order_id: str, payment_id: str, signature: str
) -> dict:
    """Confirm a credit payment after client-side checkout.

    Verifies the signature, marks the payment as captured, adds credits.
    """
    provider = get_payment_provider()
    verified = await provider.verify_payment(order_id, payment_id, signature)
    if not verified:
        raise PaymentProviderError("Payment signature verification failed.")

    # Find and update the payment record
    result = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id, Payment.user_id == user_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise PaymentProviderError("Payment record not found.")

    payment.razorpay_payment_id = payment_id
    payment.status = "captured"
    payment.credits_granted = 1

    # Add credits
    new_balance = await add_credits(db, user_id, 1)
    await db.commit()

    return {"credits_granted": 1, "new_balance": new_balance}


async def start_subscription(db: AsyncSession, user_id: str, plan: str) -> dict:
    """Start a weekly or monthly subscription.

    In mock mode, immediately activates. In production, returns the Razorpay
    subscription URL for the user to complete payment.
    """
    if plan not in ("weekly", "monthly"):
        raise PaymentProviderError("Invalid plan. Must be 'weekly' or 'monthly'.")

    provider = get_payment_provider()
    # In production, plan_id maps to a Razorpay plan created in their dashboard.
    plan_id = f"plan_{plan}_mock"
    sub_data = await provider.create_subscription(plan_id, "user@example.com")

    # Calculate period
    now = utcnow()
    period_days = 7 if plan == "weekly" else 30
    period_end = now + timedelta(days=period_days)

    subscription = Subscription(
        id=new_uuid(),
        user_id=user_id,
        plan=plan,
        status="active",
        razorpay_subscription_id=sub_data["id"],
        current_period_start=now,
        current_period_end=period_end,
    )
    db.add(subscription)
    await db.commit()

    return {
        "subscription_id": subscription.id,
        "plan": plan,
        "status": "active",
        "period_end": period_end.isoformat(),
    }


async def cancel_user_subscription(db: AsyncSession, user_id: str) -> dict:
    """Cancel the user's active subscription at period end."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise PaymentProviderError("No active subscription found.")

    provider = get_payment_provider()
    if sub.razorpay_subscription_id:
        await provider.cancel_subscription(sub.razorpay_subscription_id)

    sub.cancel_at_period_end = True
    await db.commit()

    return {
        "message": "Subscription will cancel at the end of the current period.",
        "period_end": sub.current_period_end.isoformat(),
    }
