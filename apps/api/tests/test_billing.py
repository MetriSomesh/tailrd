"""Tests for quota enforcement and billing endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def _create_verified_user(client: AsyncClient, email: str = "billing@test.com") -> None:
    """Create a verified user with completed onboarding."""
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "strongPass123!", "name": "Billing User"},
    )
    await client.patch("/api/v1/profile/basics", json={"full_name": "Billing User", "phone": "123", "email": email})
    await client.put("/api/v1/profile/educations", json=[{"degree": "BS", "institution": "U"}])
    await client.put("/api/v1/profile/experiences", json=[{"title": "SWE", "company": "Co", "bullets": ["Did x."]}])
    await client.put("/api/v1/profile/skills", json=[{"category": "Lang", "items": ["Python"]}])
    await client.post("/api/v1/profile/step", json={"step": 8})

    # Verify email directly
    from sqlalchemy import select

    from app.db.base import utcnow
    from app.db.models.user import User
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.email_verified_at = utcnow()
        await db.commit()


class TestUsage:
    async def test_returns_usage_summary(self, client: AsyncClient) -> None:
        await _create_verified_user(client)
        r = await client.get("/api/v1/billing/usage")
        assert r.status_code == 200
        body = r.json()
        assert body["free_limit"] == 3
        assert body["free_used"] == 0
        assert body["free_remaining"] == 3
        assert body["credit_balance"] == 0
        assert body["has_subscription"] is False


class TestCreditPurchase:
    async def test_create_order_returns_order_id(self, client: AsyncClient) -> None:
        await _create_verified_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post("/api/v1/billing/orders", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        body = r.json()
        assert "order_id" in body
        assert body["amount_paise"] == 2900
        assert body["currency"] == "INR"

    async def test_confirm_payment_adds_credits(self, client: AsyncClient) -> None:
        await _create_verified_user(client)
        csrf = client.cookies.get("tailrd_csrf")

        # Create order
        order_r = await client.post("/api/v1/billing/orders", headers={"X-CSRF-Token": csrf})
        order_id = order_r.json()["order_id"]

        # Confirm (mock provider always verifies)
        r = await client.post(
            "/api/v1/billing/confirm",
            json={"order_id": order_id, "payment_id": "pay_mock_123", "signature": "mock_sig"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["credits_granted"] == 1
        assert body["new_balance"] == 1

        # Verify usage shows credits
        usage_r = await client.get("/api/v1/billing/usage")
        assert usage_r.json()["credit_balance"] == 1


class TestSubscription:
    async def test_start_weekly_subscription(self, client: AsyncClient) -> None:
        await _create_verified_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan": "weekly"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["plan"] == "weekly"
        assert body["status"] == "active"
        assert "period_end" in body

        # Usage should show subscription
        usage_r = await client.get("/api/v1/billing/usage")
        assert usage_r.json()["has_subscription"] is True
        assert usage_r.json()["subscription_plan"] == "weekly"

    async def test_cancel_subscription(self, client: AsyncClient) -> None:
        await _create_verified_user(client, "cancel@test.com")
        csrf = client.cookies.get("tailrd_csrf")

        # Start subscription first
        await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan": "monthly"},
            headers={"X-CSRF-Token": csrf},
        )

        # Cancel
        r = await client.post("/api/v1/billing/cancel", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        assert "period_end" in r.json()


class TestQuotaEnforcement:
    async def test_free_tier_allows_3_resumes(self, client: AsyncClient) -> None:
        """Verify the quota service logic directly."""
        from app.db.session import get_sessionmaker
        from app.services.quota import check_and_consume_entitlement

        await _create_verified_user(client, "quota@test.com")

        # Get user_id
        me_r = await client.get("/api/v1/auth/me")
        user_id = me_r.json()["id"]

        async with get_sessionmaker()() as db:
            # First 3 should succeed
            for _ in range(3):
                source = await check_and_consume_entitlement(db, user_id)
                assert source == "free"
            await db.commit()

            # 4th should fail
            import pytest

            from app.core.errors import QuotaExceededError

            with pytest.raises(QuotaExceededError):
                await check_and_consume_entitlement(db, user_id)

    async def test_credits_consumed_after_free_exhausted(self, client: AsyncClient) -> None:
        """After free tier is used up, credits are consumed."""
        from app.db.session import get_sessionmaker
        from app.services.quota import add_credits, check_and_consume_entitlement

        await _create_verified_user(client, "credits@test.com")
        me_r = await client.get("/api/v1/auth/me")
        user_id = me_r.json()["id"]

        async with get_sessionmaker()() as db:
            # Use up free tier
            for _ in range(3):
                await check_and_consume_entitlement(db, user_id)

            # Add 2 credits
            await add_credits(db, user_id, 2)
            await db.commit()

            # Next should consume credit
            source = await check_and_consume_entitlement(db, user_id)
            assert source == "credit"
            await db.commit()

    async def test_subscription_gives_unlimited(self, client: AsyncClient) -> None:
        """Subscribed users bypass free tier and credits."""
        from app.db.session import get_sessionmaker
        from app.services.quota import check_and_consume_entitlement

        await _create_verified_user(client, "subquota@test.com")
        csrf = client.cookies.get("tailrd_csrf")

        # Start subscription
        await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan": "monthly"},
            headers={"X-CSRF-Token": csrf},
        )

        me_r = await client.get("/api/v1/auth/me")
        user_id = me_r.json()["id"]

        async with get_sessionmaker()() as db:
            # Should always return "subscription"
            for _ in range(10):
                source = await check_and_consume_entitlement(db, user_id)
                assert source == "subscription"
            await db.commit()
