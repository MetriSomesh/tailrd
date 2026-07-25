"""Billing models: usage counters, subscriptions, payments, credits."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UsageCounter(Base, UUIDPrimaryKeyMixin):
    """Tracks free-tier resume usage per calendar month."""

    __tablename__ = "usage_counters"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Period start as "YYYY-MM" string for easy querying without timezone gymnastics.
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # e.g. "2026-07"
    resumes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CreditBalance(Base, UUIDPrimaryKeyMixin):
    """Per-user credit balance (from ₹29 one-off purchases). Never expires."""

    __tablename__ = "credit_balances"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Active subscription (weekly or monthly unlimited plan)."""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)  # "weekly" | "monthly"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # active | cancelled | expired
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(100))
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual payment record (one-off credit purchase or subscription charge)."""

    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100))
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "one_off" | "subscription"
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending | captured | failed | refunded
    credits_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class WebhookEvent(Base, UUIDPrimaryKeyMixin):
    """Idempotency guard: tracks processed webhook events."""

    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    event_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
