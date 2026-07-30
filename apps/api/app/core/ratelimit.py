"""Redis-backed fixed-window rate limiting.

Applied as a route dependency to abuse-prone endpoints (login, signup, the
email-sending flows, and tailor submission). Uses the shared Redis client (so it
transparently uses fakeredis in dev/tests) and fails OPEN if Redis is down — a
cache outage should throttle nothing rather than lock everyone out.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from app.core.config import settings
from app.core.errors import RateLimitedError
from app.core.logging import get_logger
from app.services.cache import get_redis, safe_incr

log = get_logger(__name__)


def _client_ip(request: Request) -> str:
    """Best-effort client IP.

    Behind a trusted proxy (Caddy overwrites X-Forwarded-For) the real client is
    the left-most XFF entry. Without that guarantee we use the socket peer, since
    a client-supplied XFF would be spoofable.
    """
    if settings.TRUST_PROXY_HEADERS:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
    return request.client.host if request.client else "unknown"


async def enforce(request: Request, *, scope: str, limit: int, window: int) -> None:
    """Count this request against `scope` for the client IP; raise 429 if over.

    Fixed window: INCR a key with a `window`-second TTL. `limit` requests are
    allowed per window.
    """
    if not settings.RATE_LIMIT_ENABLED or limit <= 0:
        return

    ip = _client_ip(request)
    key = f"rl:{scope}:{ip}"

    count = await safe_incr(key, ttl=window)
    if count is None:
        # Redis unavailable — fail open (don't block legitimate traffic).
        return

    if count > limit:
        retry_after = window
        try:
            ttl = await get_redis().ttl(key)
            if isinstance(ttl, int) and ttl > 0:
                retry_after = ttl
        except Exception:  # noqa: BLE001, S110 - TTL is best-effort
            pass
        log.warning("rate_limited", scope=scope, ip=ip, count=count, limit=limit)
        raise RateLimitedError(
            "Too many requests. Please slow down and try again shortly.",
            retry_after=retry_after,
        )


def rate_limit(scope: str, limit: int, window: int) -> Callable[[Request], Awaitable[None]]:
    """Build a FastAPI dependency that enforces a limit for `scope`."""

    async def _dep(request: Request) -> None:
        await enforce(request, scope=scope, limit=limit, window=window)

    return _dep
