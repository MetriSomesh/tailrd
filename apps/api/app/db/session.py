"""Async SQLAlchemy engine and session management.

Pool sizes are deliberately small: the target host has 1 GB RAM and Neon's
free tier has a low connection ceiling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    url = settings.DATABASE_URL
    kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
    }

    if url.startswith("sqlite"):
        # SQLite (local dev / tests).
        # NullPool: no connection reuse. Avoids the MissingGreenlet error caused
        # by aiosqlite connections being used across different async tasks.
        from sqlalchemy.pool import NullPool

        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=1800,
            connect_args={
                "options": f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}",
            },
        )

    return create_async_engine(url, **kwargs)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a session that always closes."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database() -> tuple[bool, str]:
    """Readiness check. Returns (ok, detail)."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:  # noqa: BLE001 - probe must never raise
        return False, type(exc).__name__


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        log.info("database_engine_disposed")
    _engine = None
    _sessionmaker = None
