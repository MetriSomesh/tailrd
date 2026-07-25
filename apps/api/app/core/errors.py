"""Typed application errors mapped to RFC 9457 Problem Details responses.

Every error the API returns has a stable machine-readable `code` so the
frontend can branch on it without string-matching human messages.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all expected application errors.

    Unexpected exceptions are caught by the global handler and returned as a
    generic 500 without leaking internals.
    """

    status_code: int = 500
    code: str = "internal_error"
    title: str = "Internal Server Error"
    # Safe to show the user verbatim?
    public: bool = True

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.detail = detail or self.title
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.extra = extra or {}
        self.retry_after = retry_after
        super().__init__(self.detail)

    def to_problem(self, instance: str | None = None) -> dict[str, Any]:
        problem: dict[str, Any] = {
            "type": f"https://tailrd.app/errors/{self.code}",
            "title": self.title,
            "status": self.status_code,
            "code": self.code,
            "detail": self.detail if self.public else self.title,
        }
        if instance:
            problem["instance"] = instance
        if self.extra:
            problem.update(self.extra)
        return problem


# ---------------------------------------------------------------------------
# 4xx — client errors
# ---------------------------------------------------------------------------


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    title = "Validation Failed"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    title = "Bad Request"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthenticated"
    title = "Authentication Required"


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    title = "Invalid Email or Password"


class TokenExpiredError(AuthenticationError):
    code = "token_expired"
    title = "Session Expired"


class TokenInvalidError(AuthenticationError):
    code = "token_invalid"
    title = "Invalid Token"


class EmailNotVerifiedError(AppError):
    status_code = 403
    code = "email_not_verified"
    title = "Email Not Verified"


class AuthorizationError(AppError):
    status_code = 403
    code = "forbidden"
    title = "Forbidden"


class CSRFError(AppError):
    status_code = 403
    code = "csrf_failed"
    title = "CSRF Validation Failed"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    title = "Not Found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    title = "Conflict"


class EmailAlreadyRegisteredError(ConflictError):
    code = "email_already_registered"
    title = "Email Already Registered"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"
    title = "Payload Too Large"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "unsupported_media_type"
    title = "Unsupported Media Type"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    title = "Too Many Requests"


class QuotaExceededError(AppError):
    """User is out of free resumes / credits and has no active subscription."""

    status_code = 402
    code = "quota_exceeded"
    title = "Payment Required"


class FairUseExceededError(AppError):
    """Subscriber hit the documented daily/period fair-use ceiling."""

    status_code = 429
    code = "fair_use_exceeded"
    title = "Fair Use Limit Reached"


class OnboardingIncompleteError(AppError):
    status_code = 409
    code = "onboarding_incomplete"
    title = "Profile Incomplete"


# ---------------------------------------------------------------------------
# 5xx — server / dependency errors
# ---------------------------------------------------------------------------


class InternalError(AppError):
    status_code = 500
    code = "internal_error"
    title = "Internal Server Error"
    public = False


class DependencyError(AppError):
    """A required downstream dependency failed."""

    status_code = 503
    code = "dependency_unavailable"
    title = "Service Temporarily Unavailable"


class DatabaseUnavailableError(DependencyError):
    code = "database_unavailable"
    title = "Database Temporarily Unavailable"


class QueueUnavailableError(DependencyError):
    code = "queue_unavailable"
    title = "Job Queue Temporarily Unavailable"


class StorageError(DependencyError):
    code = "storage_unavailable"
    title = "File Storage Temporarily Unavailable"


class EmailDeliveryError(DependencyError):
    code = "email_delivery_failed"
    title = "Could Not Send Email"


class PaymentProviderError(DependencyError):
    code = "payment_provider_error"
    title = "Payment Provider Error"


class AgentUnavailableError(DependencyError):
    code = "agent_unavailable"
    title = "Resume Engine Temporarily Unavailable"


class AgentTimeoutError(DependencyError):
    status_code = 504
    code = "agent_timeout"
    title = "Resume Engine Timed Out"


class AgentOutputInvalidError(AppError):
    """The agent returned something that failed schema validation."""

    status_code = 502
    code = "agent_output_invalid"
    title = "Resume Engine Returned Invalid Output"


class CircuitOpenError(DependencyError):
    code = "circuit_open"
    title = "Service Paused After Repeated Failures"


# Error codes for which a consumed entitlement should be refunded.
REFUNDABLE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "internal_error",
        "dependency_unavailable",
        "agent_unavailable",
        "agent_timeout",
        "agent_output_invalid",
        "circuit_open",
        "storage_unavailable",
        "queue_unavailable",
        "database_unavailable",
    }
)
