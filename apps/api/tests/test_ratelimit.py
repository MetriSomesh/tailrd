"""Tests for the Redis-backed rate limiter."""

from __future__ import annotations

from httpx import AsyncClient

from app.core import ratelimit
from app.core.config import settings


class TestLoginRateLimit:
    async def test_blocks_after_limit(self, client: AsyncClient, monkeypatch) -> None:
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
        body = {"email": "rl@example.com", "password": "whatever123"}

        statuses = []
        for _ in range(settings.RL_LOGIN_PER_15MIN + 1):
            r = await client.post("/api/v1/auth/login", json=body)
            statuses.append(r.status_code)

        # The first N are allowed through to auth (401 — no such user); the next
        # one is throttled.
        assert statuses[-1] == 429
        assert statuses[: settings.RL_LOGIN_PER_15MIN] == [401] * settings.RL_LOGIN_PER_15MIN

        last = await client.post("/api/v1/auth/login", json=body)
        assert last.status_code == 429
        assert last.json()["code"] == "rate_limited"
        assert "retry-after" in {k.lower() for k in last.headers}

    async def test_disabled_by_default(self, client: AsyncClient) -> None:
        # conftest sets RATE_LIMIT_ENABLED=false → no throttling.
        body = {"email": "rl2@example.com", "password": "whatever123"}
        for _ in range(settings.RL_LOGIN_PER_15MIN + 3):
            r = await client.post("/api/v1/auth/login", json=body)
            assert r.status_code == 401  # never 429


class TestEnforceUnit:
    async def test_fails_open_when_redis_down(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)

        async def _no_redis(*_a, **_k):
            return None  # safe_incr returns None when Redis is unavailable

        monkeypatch.setattr(ratelimit, "safe_incr", _no_redis)

        class _Req:
            headers: dict = {}
            client = type("C", (), {"host": "1.2.3.4"})()

        # Should not raise even far "over" the limit — degrade open.
        for _ in range(50):
            await ratelimit.enforce(_Req(), scope="x", limit=1, window=60)

    def test_client_ip_prefers_xff_when_trusted(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)

        class _Req:
            headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
            client = type("C", (), {"host": "10.0.0.1"})()

        assert ratelimit._client_ip(_Req()) == "203.0.113.7"

    def test_client_ip_ignores_xff_when_untrusted(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)

        class _Req:
            headers = {"x-forwarded-for": "203.0.113.7"}
            client = type("C", (), {"host": "10.0.0.1"})()

        assert ratelimit._client_ip(_Req()) == "10.0.0.1"
