"""Redis access with graceful degradation.

Redis is used for the job queue, rate limits, the agent lock, and the circuit
breaker. If it is unavailable the API must degrade (reject new tailor jobs) not
crash (auth and reads keep working).
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a shared Redis client.

    Uses fakeredis when REDIS_FAKE is set so local dev and tests do not need a
    running server.
    """
    global _client
    if _client is not None:
        return _client

    if settings.REDIS_FAKE:
        import fakeredis.aioredis

        _client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        log.info("redis_fake_enabled")
        return _client

    _client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
        # Keep the pool tiny; 1 GB host.
        max_connections=10,
    )
    return _client


async def check_redis() -> tuple[bool, str]:
    """Readiness check. Returns (ok, detail). Never raises."""
    try:
        client = get_redis()
        pong = await client.ping()
        return bool(pong), "connected" if pong else "no_pong"
    except Exception as exc:  # noqa: BLE001 - probe must never raise
        return False, type(exc).__name__


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
            log.info("redis_closed")
        except Exception as exc:  # noqa: BLE001 - shutdown must not raise
            log.warning("redis_close_failed", error=type(exc).__name__)
    _client = None


# ---------------------------------------------------------------------------
# Safe helpers: return a fallback instead of raising when Redis is down.
# ---------------------------------------------------------------------------


async def safe_get(key: str, default: Any = None) -> Any:
    try:
        return await get_redis().get(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("redis_get_failed", key=key, error=type(exc).__name__)
        return default


async def safe_set(key: str, value: str, ttl: int | None = None) -> bool:
    try:
        await get_redis().set(key, value, ex=ttl)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("redis_set_failed", key=key, error=type(exc).__name__)
        return False


async def safe_incr(key: str, ttl: int | None = None) -> int | None:
    """Increment a counter, setting a TTL on first write.

    Returns the new value, or None if Redis is unavailable.
    """
    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.incr(key)
        if ttl is not None:
            pipe.expire(key, ttl, nx=True)
        results = await pipe.execute()
        return int(results[0])
    except Exception as exc:  # noqa: BLE001
        log.warning("redis_incr_failed", key=key, error=type(exc).__name__)
        return None


async def safe_delete(*keys: str) -> bool:
    if not keys:
        return True
    try:
        await get_redis().delete(*keys)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("redis_delete_failed", error=type(exc).__name__)
        return False
