"""SQLAlchemy declarative base and shared column conventions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming convention so Alembic autogenerate produces stable,
# predictable constraint names instead of database-specific defaults.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware UTC now.

    Always use this instead of datetime.utcnow(), which returns a naive
    datetime and silently breaks comparisons against aware columns.
    """
    return datetime.now(UTC)


def new_uuid() -> str:
    """UUID4 as a 32-char hex string.

    Stored as a string rather than a native UUID type so the same schema works
    on both SQLite (local/test) and PostgreSQL (production) without dialect
    branching.
    """
    return uuid.uuid4().hex


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid, index=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
