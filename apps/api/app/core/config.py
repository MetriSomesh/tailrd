"""Application configuration, loaded from environment with validation.

Fails fast at startup if required production settings are missing, rather than
failing at first request.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Core ----
    ENVIRONMENT: Environment = "local"
    APP_NAME: str = "Tailrd"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ---- URLs ----
    # Public URL of the frontend, used for OAuth redirects and email links.
    FRONTEND_URL: str = "http://localhost:3000"
    # Public URL of this API.
    BACKEND_URL: str = "http://localhost:8000"
    # Comma-separated list of allowed CORS origins.
    CORS_ORIGINS: str = "http://localhost:3000"

    # ---- Security ----
    # 32+ byte random secret. Auto-generated in local/test, REQUIRED in prod.
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ACCESS_TOKEN_TTL_SECONDS: int = 900  # 15 minutes
    REFRESH_TOKEN_TTL_SECONDS: int = 60 * 60 * 24 * 30  # 30 days
    EMAIL_VERIFY_TTL_SECONDS: int = 60 * 60 * 24  # 24 hours
    PASSWORD_RESET_TTL_SECONDS: int = 60 * 60  # 1 hour
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = False  # forced True in production by validator
    SESSION_COOKIE_NAME: str = "tailrd_at"
    REFRESH_COOKIE_NAME: str = "tailrd_rt"
    CSRF_COOKIE_NAME: str = "tailrd_csrf"

    # ---- Database ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./tailrd_dev.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT: int = 10
    DB_STATEMENT_TIMEOUT_MS: int = 15_000

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"
    # When true, use an in-memory fake (local dev without Redis installed).
    REDIS_FAKE: bool = False

    # ---- Google OAuth ----
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # ---- Email ----
    # console = print to stdout (dev). resend = real delivery.
    EMAIL_PROVIDER: Literal["console", "resend"] = "console"
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "Tailrd <no-reply@tailrd.local>"

    # ---- Storage ----
    # local = filesystem (dev). s3 = AWS S3.
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_DIR: str = "./_storage"
    S3_BUCKET: str | None = None
    S3_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    PRESIGNED_URL_TTL_SECONDS: int = 300

    # ---- Payments ----
    # mock = no network, deterministic (dev/test). razorpay = live integration.
    PAYMENT_PROVIDER: Literal["mock", "razorpay"] = "mock"
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    # ---- Agent (Hermes + OpenCode) ----
    AGENT_ENABLED: bool = True
    # mock     = deterministic stub (tests/dev). No LLM.
    # opencode = spawn the `opencode` CLI per job (subprocess + workspace).
    # openai   = call an OpenAI-compatible endpoint (e.g. the local OpenCode/Zen
    #            proxy that Hermes uses, or Zen cloud). This is the recommended
    #            production path — no per-job subprocess.
    AGENT_BACKEND: Literal["mock", "opencode", "openai"] = "mock"
    AGENT_COMMAND: str = "opencode"
    AGENT_WORKSPACE_ROOT: str = "./_agent_workspaces"
    AGENT_SKILL_DIR: str = "../../agent/skills"
    AGENT_TIMEOUT_SECONDS: int = 180
    # Model id. For opencode: `provider/model` (run `opencode models`). For the
    # openai backend: whatever the endpoint expects (e.g. "deepseek-v4-flash-free"
    # via the local proxy, or an OpenCode Zen model). None → backend default.
    AGENT_MODEL: str | None = None
    # Auto-approve tool permissions so the opencode CLI can write files unattended.
    AGENT_AUTO_APPROVE: bool = True
    # OpenCode Zen API key. For opencode: injected as OPENCODE_API_KEY env (also
    # settable via `opencode auth login`).
    OPENCODE_API_KEY: str | None = None

    # Hard cap on resume-parse LLM extraction. The frontend proxy is configured
    # to tolerate this (experimental.proxyTimeout), so we allow the full ~35s
    # opencode run; this only guards against a runaway/hung model, after which we
    # fall back to the fast heuristic so the upload never hangs or 500s.
    RESUME_PARSE_TIMEOUT_SECONDS: int = 90

    # ---- OpenAI-compatible agent backend (AGENT_BACKEND=openai) ----
    # Base URL of the OpenAI-compatible endpoint. Defaults to the local OpenCode
    # proxy that Hermes points at; can be Zen cloud (https://opencode.ai/zen/v1)
    # or any OpenAI-compatible server (Ollama, LM Studio, OpenRouter, ...).
    AGENT_API_BASE_URL: str = "http://127.0.0.1:9876/v1"
    # API key for that endpoint. Local proxies usually accept any/no key; a dummy
    # is sent when unset so SDKs that require a bearer token still work.
    AGENT_API_KEY: str | None = None
    AGENT_LOCK_KEY: str = "tailrd:agent:lock"
    AGENT_LOCK_TTL_SECONDS: int = 200
    AGENT_MAX_RETRIES: int = 2
    # Circuit breaker
    AGENT_BREAKER_THRESHOLD: int = 3
    AGENT_BREAKER_COOLDOWN_SECONDS: int = 300

    # ---- Tailoring pipeline ----
    TARGET_SCORE: float = 70.0
    MAX_ITERATIONS: int = 3

    # ---- Quota / entitlements ----
    FREE_RESUMES_PER_MONTH: int = 3
    FREE_RESUMES_PER_DAY: int = 3
    CREDIT_RESUMES_PER_DAY: int = 10
    SUB_RESUMES_PER_DAY: int = 15
    SUB_WEEKLY_RESUMES_PER_PERIOD: int = 60
    SUB_MONTHLY_RESUMES_PER_PERIOD: int = 150

    # ---- Pricing (paise) ----
    PRICE_PER_RESUME_PAISE: int = 2900  # Rs 29
    PRICE_WEEKLY_PAISE: int = 14900  # Rs 149
    PRICE_MONTHLY_PAISE: int = 34900  # Rs 349

    # ---- Worker ----
    WORKER_ENABLED: bool = True
    WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    WORKER_CONCURRENCY: int = 1
    JOB_QUEUE_KEY: str = "tailrd:jobs"
    JOB_MAX_ATTEMPTS: int = 3

    # ---- Rate limits (requests per window) ----
    RL_LOGIN_PER_15MIN: int = 5
    RL_SIGNUP_PER_HOUR: int = 3
    RL_TAILOR_PER_HOUR: int = 10
    RL_JD_FETCH_PER_HOUR: int = 20
    RL_PUBLIC_PREVIEW_PER_HOUR: int = 10

    # ---- Uploads ----
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # ---- Observability ----
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # ---- Data retention (days) ----
    RETAIN_DOCX_DAYS: int = 90
    RETAIN_RUNS_DAYS: int = 365
    ACCOUNT_DELETION_GRACE_DAYS: int = 30

    # ------------------------------------------------------------------
    # Derived / validated
    # ------------------------------------------------------------------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return v

    def validate_for_runtime(self) -> list[str]:
        """Return a list of fatal misconfigurations. Empty means OK.

        Called at startup so the process refuses to boot half-configured
        rather than failing on the first user request.
        """
        problems: list[str] = []

        if self.is_production:
            if len(self.SECRET_KEY) < 32:
                problems.append("SECRET_KEY must be at least 32 chars in production")
            if not self.COOKIE_SECURE:
                problems.append("COOKIE_SECURE must be true in production")
            if self.DATABASE_URL.startswith("sqlite"):
                problems.append("SQLite is not supported in production; use PostgreSQL")
            if self.DEBUG:
                problems.append("DEBUG must be false in production")
            if self.EMAIL_PROVIDER == "console":
                problems.append("EMAIL_PROVIDER must not be 'console' in production")
            if self.PAYMENT_PROVIDER == "mock":
                problems.append("PAYMENT_PROVIDER must not be 'mock' in production")
            if self.STORAGE_BACKEND == "local":
                problems.append("STORAGE_BACKEND must be 's3' in production")

        if self.EMAIL_PROVIDER == "resend" and not self.RESEND_API_KEY:
            problems.append("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")

        if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET:
            problems.append("S3_BUCKET is required when STORAGE_BACKEND=s3")

        if self.PAYMENT_PROVIDER == "razorpay":
            if not self.RAZORPAY_KEY_ID or not self.RAZORPAY_KEY_SECRET:
                problems.append("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")
            if not self.RAZORPAY_WEBHOOK_SECRET:
                problems.append("RAZORPAY_WEBHOOK_SECRET is required for webhook verification")

        # The real agent needs credentials for the model gateway. In production we
        # require the key via env; locally it may come from `opencode auth login`.
        if self.is_production and self.AGENT_BACKEND == "opencode" and not self.OPENCODE_API_KEY:
            problems.append("OPENCODE_API_KEY is required when AGENT_BACKEND=opencode in production")

        if (self.GOOGLE_CLIENT_ID is None) != (self.GOOGLE_CLIENT_SECRET is None):
            problems.append("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set together")

        if self.MAX_ITERATIONS < 1:
            problems.append("MAX_ITERATIONS must be >= 1")

        return problems


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
