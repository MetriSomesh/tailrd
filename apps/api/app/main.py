"""Tailrd API entrypoint.

Design notes:
- Fails fast at startup on misconfiguration rather than at first request.
- Registers global exception handlers so no code path returns a stack trace.
- Runs the job worker in-process (memory constraint: single 1 GB host).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import health

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()

    problems = settings.validate_for_runtime()
    if problems:
        for p in problems:
            log.error("config_invalid", problem=p)
        raise RuntimeError(
            f"Refusing to start with {len(problems)} configuration problem(s): "
            + "; ".join(problems)
        )

    log.info(
        "startup",
        app=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        agent_backend=settings.AGENT_BACKEND,
        payment_provider=settings.PAYMENT_PROVIDER,
        storage_backend=settings.STORAGE_BACKEND,
        email_provider=settings.EMAIL_PROVIDER,
        worker_enabled=settings.WORKER_ENABLED,
    )

    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        log.info("sentry_initialised")

    # Warm the DB connection so a bad DATABASE_URL surfaces now, not later.
    from app.db.session import check_database, get_engine

    # Auto-create tables in local/test (SQLite). Production uses Alembic.
    if settings.DATABASE_URL.startswith("sqlite"):
        import app.db.models  # noqa: F401 — side-effect: registers models with metadata
        from app.db.base import Base

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    db_ok, db_detail = await check_database()
    if not db_ok:
        log.warning("database_unreachable_at_startup", detail=db_detail)

    worker_task: asyncio.Task[None] | None = None
    if settings.WORKER_ENABLED:
        from app.workers.runner import worker_loop

        worker_task = asyncio.create_task(worker_loop(), name="tailrd-worker")
        log.info("worker_started", concurrency=settings.WORKER_CONCURRENCY)

    try:
        yield
    finally:
        log.info("shutdown_initiated")

        if worker_task is not None:
            worker_task.cancel()
            try:
                await asyncio.wait_for(worker_task, timeout=30)
            except (TimeoutError, asyncio.CancelledError):
                log.warning("worker_shutdown_forced")
            except Exception:  # noqa: BLE001
                log.exception("worker_shutdown_error")

        from app.db.session import dispose_engine
        from app.services.cache import close_redis

        await close_redis()
        await dispose_engine()
        log.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="0.1.0",
        description="AI resume tailoring as a service.",
        lifespan=lifespan,
        # Hide interactive docs in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # Order matters: the outermost middleware is added last.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_UPLOAD_BYTES)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)

    # Auth routes
    from app.routers import account, auth, billing, profile, tailor

    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(account.router, prefix=settings.API_V1_PREFIX)
    app.include_router(profile.router, prefix=settings.API_V1_PREFIX)
    app.include_router(tailor.router, prefix=settings.API_V1_PREFIX)
    app.include_router(billing.router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
