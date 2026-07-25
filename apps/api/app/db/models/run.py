"""TailorRun model: tracks each resume tailoring job through its lifecycle.

States: queued → running → succeeded | failed | cancelled
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TailorRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tailor_runs"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Job state
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )  # queued | running | succeeded | failed | cancelled

    # Input
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_url: Mapped[str | None] = mapped_column(String(2048))
    jd_label: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(200))

    # Output (populated on success)
    tailored_json: Mapped[str | None] = mapped_column(Text)  # JSON string
    score_json: Mapped[str | None] = mapped_column(Text)  # JSON string
    parsability_json: Mapped[str | None] = mapped_column(Text)  # JSON string
    overall_score: Mapped[float | None] = mapped_column(Float)
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # File reference (S3 key or local path)
    docx_storage_key: Mapped[str | None] = mapped_column(String(500))

    # Error info (populated on failure)
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Entitlement tracking (for refunds on system errors)
    entitlement_consumed: Mapped[bool] = mapped_column(default=False, nullable=False)
    entitlement_refunded: Mapped[bool] = mapped_column(default=False, nullable=False)
