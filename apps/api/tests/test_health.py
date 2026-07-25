"""Phase 0 smoke tests: the app boots, probes work, errors are well-formed."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealth:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        r = await client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["environment"] == "test"
        assert "uptime_seconds" in body

    async def test_health_sets_request_id_header(self, client: AsyncClient) -> None:
        r = await client.get("/health")
        assert r.headers.get("x-request-id")

    async def test_health_echoes_incoming_request_id(self, client: AsyncClient) -> None:
        r = await client.get("/health", headers={"X-Request-ID": "abc123"})
        assert r.headers["x-request-id"] == "abc123"


class TestReady:
    async def test_ready_reports_checks(self, client: AsyncClient) -> None:
        r = await client.get("/ready")
        # In-memory SQLite + fakeredis should both be reachable.
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"]["ok"] is True
        assert body["checks"]["redis"]["ok"] is True
        assert body["degraded"] is False


class TestSecurityHeaders:
    @pytest.mark.parametrize(
        "header,expected",
        [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ],
    )
    async def test_security_headers_present(
        self, client: AsyncClient, header: str, expected: str
    ) -> None:
        r = await client.get("/health")
        assert r.headers.get(header) == expected

    async def test_no_hsts_outside_production(self, client: AsyncClient) -> None:
        r = await client.get("/health")
        assert "Strict-Transport-Security" not in r.headers

    async def test_csp_present(self, client: AsyncClient) -> None:
        r = await client.get("/health")
        assert "default-src 'none'" in r.headers.get("Content-Security-Policy", "")


class TestErrorHandling:
    async def test_unknown_route_returns_problem_json(self, client: AsyncClient) -> None:
        r = await client.get("/definitely-not-a-route")
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/problem+json")
        body = r.json()
        assert body["code"] == "not_found"
        assert body["status"] == 404
        assert "request_id" in body

    async def test_method_not_allowed_is_problem_json(self, client: AsyncClient) -> None:
        r = await client.post("/health")
        assert r.status_code == 405
        body = r.json()
        assert body["status"] == 405
        assert "code" in body

    async def test_error_response_never_leaks_traceback(self, client: AsyncClient) -> None:
        r = await client.get("/definitely-not-a-route")
        text = r.text.lower()
        for leak in ("traceback", 'file "', '.py", line', "starlette."):
            assert leak not in text


class TestConfigValidation:
    def test_production_rejects_insecure_defaults(self) -> None:
        from app.core.config import Settings

        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short",
            COOKIE_SECURE=False,
            DEBUG=True,
            DATABASE_URL="sqlite+aiosqlite:///./x.db",
            EMAIL_PROVIDER="console",
            PAYMENT_PROVIDER="mock",
            STORAGE_BACKEND="local",
        )
        problems = s.validate_for_runtime()
        joined = " ".join(problems)
        assert "SECRET_KEY" in joined
        assert "COOKIE_SECURE" in joined
        assert "SQLite" in joined
        assert "DEBUG" in joined
        assert "EMAIL_PROVIDER" in joined
        assert "PAYMENT_PROVIDER" in joined
        assert "STORAGE_BACKEND" in joined

    def test_local_defaults_are_valid(self) -> None:
        from app.core.config import Settings

        s = Settings(ENVIRONMENT="local")
        assert s.validate_for_runtime() == []

    def test_oauth_credentials_must_be_paired(self) -> None:
        from app.core.config import Settings

        s = Settings(ENVIRONMENT="local", GOOGLE_CLIENT_ID="only-id")
        problems = s.validate_for_runtime()
        assert any("GOOGLE_CLIENT" in p for p in problems)

    def test_resend_requires_api_key(self) -> None:
        from app.core.config import Settings

        s = Settings(ENVIRONMENT="local", EMAIL_PROVIDER="resend")
        assert any("RESEND_API_KEY" in p for p in s.validate_for_runtime())

    def test_invalid_log_level_rejected(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.core.config import Settings

        with pytest.raises(PydanticValidationError):
            Settings(LOG_LEVEL="LOUD")


class TestErrorTaxonomy:
    def test_problem_shape(self) -> None:
        from app.core.errors import QuotaExceededError

        err = QuotaExceededError("Out of free resumes.")
        problem = err.to_problem(instance="/api/v1/tailor")
        assert problem["status"] == 402
        assert problem["code"] == "quota_exceeded"
        assert problem["instance"] == "/api/v1/tailor"
        assert problem["detail"] == "Out of free resumes."

    def test_non_public_error_hides_detail(self) -> None:
        from app.core.errors import InternalError

        err = InternalError("database password is hunter2")
        problem = err.to_problem()
        assert "hunter2" not in problem["detail"]
        assert problem["detail"] == "Internal Server Error"

    def test_refundable_codes_cover_dependency_failures(self) -> None:
        from app.core.errors import (
            REFUNDABLE_ERROR_CODES,
            AgentTimeoutError,
            AgentUnavailableError,
            CircuitOpenError,
        )

        for exc in (AgentUnavailableError, AgentTimeoutError, CircuitOpenError):
            assert exc.code in REFUNDABLE_ERROR_CODES

    def test_user_errors_are_not_refundable(self) -> None:
        from app.core.errors import (
            REFUNDABLE_ERROR_CODES,
            QuotaExceededError,
            ValidationError,
        )

        assert QuotaExceededError.code not in REFUNDABLE_ERROR_CODES
        assert ValidationError.code not in REFUNDABLE_ERROR_CODES
