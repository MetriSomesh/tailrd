"""Shared pytest fixtures.

Environment is forced into a hermetic test configuration before the app
imports settings, so tests never touch real Redis, S3, email, or payments.
"""

from __future__ import annotations

import os

# Must run before `app.core.config` is imported anywhere.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_JSON": "false",
        "LOG_LEVEL": "WARNING",
        "SECRET_KEY": "test-secret-key-that-is-definitely-long-enough-000000",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_FAKE": "true",
        "EMAIL_PROVIDER": "console",
        "STORAGE_BACKEND": "local",
        "PAYMENT_PROVIDER": "mock",
        "AGENT_BACKEND": "mock",
        "WORKER_ENABLED": "false",
        "COOKIE_SECURE": "false",
    }
)

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def app():
    """Fresh app instance per test, with lifespan run."""
    from asgi_lifespan import LifespanManager

    from app.main import create_app

    application = create_app()
    async with LifespanManager(application, startup_timeout=30, shutdown_timeout=30):
        yield application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
async def _reset_singletons():
    """Clear module-level singletons between tests to avoid cross-test leakage."""
    yield
    from app.services import cache

    await cache.close_redis()
