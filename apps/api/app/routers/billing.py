"""Billing routes: usage, credit purchase, subscriptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_verified_user, require_csrf
from app.db.models.user import User
from app.db.session import get_session
from app.services import payments as payment_service
from app.services.quota import get_usage_summary

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UsageSummary(BaseModel):
    has_subscription: bool
    subscription_plan: str | None = None
    subscription_ends: str | None = None
    credit_balance: int
    free_used: int
    free_limit: int
    free_remaining: int
    period: str


class OrderResponse(BaseModel):
    order_id: str
    amount_paise: int
    currency: str
    key_id: str


class ConfirmPaymentRequest(BaseModel):
    order_id: str = Field(min_length=1)
    payment_id: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class ConfirmPaymentResponse(BaseModel):
    credits_granted: int
    new_balance: int


class SubscriptionRequest(BaseModel):
    plan: str = Field(pattern="^(weekly|monthly)$")


class SubscriptionResponse(BaseModel):
    subscription_id: str
    plan: str
    status: str
    period_end: str


class CancelResponse(BaseModel):
    message: str
    period_end: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/usage", response_model=UsageSummary)
async def get_usage(
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Get the user's current entitlement status."""
    return await get_usage_summary(db, user.id)


@router.post("/orders", response_model=OrderResponse, dependencies=[Depends(require_csrf)])
async def create_credit_order(
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a ₹29 payment order for 1 resume credit."""
    return await payment_service.purchase_credits(db, user.id)


@router.post("/confirm", response_model=ConfirmPaymentResponse, dependencies=[Depends(require_csrf)])
async def confirm_payment(
    body: ConfirmPaymentRequest,
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Confirm a credit payment after client-side Razorpay checkout."""
    return await payment_service.confirm_credit_payment(
        db, user.id, body.order_id, body.payment_id, body.signature
    )


@router.post("/subscriptions", response_model=SubscriptionResponse, dependencies=[Depends(require_csrf)])
async def create_subscription(
    body: SubscriptionRequest,
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Start a weekly or monthly subscription."""
    return await payment_service.start_subscription(db, user.id, body.plan)


@router.post("/cancel", response_model=CancelResponse, dependencies=[Depends(require_csrf)])
async def cancel_subscription(
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Cancel the current subscription at the end of the billing period."""
    return await payment_service.cancel_user_subscription(db, user.id)
