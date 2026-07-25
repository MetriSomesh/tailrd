"""DPDP Act 2023 consent record.

Every user has at least one consent record (created at signup). Stores the
policy version they agreed to, so we can identify users who need to re-consent
when the policy changes.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ConsentRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "consent_records"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
