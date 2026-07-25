"""Liveness and readiness probes.

/health  — is the process alive? Never touches dependencies. Used by systemd.
/ready   — can it serve traffic? Checks DB and Redis. Used by the load balancer
           so an unhealthy instance stops receiving requests instead of erroring.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(tags=["system"])
log = get_logger(__name__)

_STARTED_AT = time.time()


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
    }


@router.get("/ready", summary="Readiness probe")
async def ready(response: Response) -> dict[str, Any]:
    from app.db.session import check_database
    from app.services.cache import check_redis

    checks: dict[str, dict[str, Any]] = {}

    db_ok, db_detail = await check_database()
    checks["database"] = {"ok": db_ok, "detail": db_detail}

    redis_ok, redis_detail = await check_redis()
    checks["redis"] = {"ok": redis_ok, "detail": redis_detail}

    # The DB is required to serve anything meaningful. Redis being down degrades
    # the tailor endpoint but auth and reads still work, so it does not fail
    # readiness on its own.
    overall = db_ok
    if not overall:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if overall else "not_ready",
        "degraded": overall and not redis_ok,
        "checks": checks,
    }
