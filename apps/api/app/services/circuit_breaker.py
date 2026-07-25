"""Circuit breaker for the agent subprocess.

After THRESHOLD consecutive failures, the circuit opens and rejects new calls
for COOLDOWN seconds. This prevents:
1. Queue backup when the agent process is broken
2. Wasted user wait time on a known-dead service
3. CPU spin on retry loops on a 1 GB host

States:
  CLOSED  → normal operation, calls pass through
  OPEN    → all calls immediately rejected with CircuitOpenError
  (no half-open state — too complex for the value on a single-host setup;
   cooldown expiry implicitly resets to CLOSED)
"""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.errors import CircuitOpenError
from app.core.logging import get_logger

log = get_logger(__name__)


class CircuitBreaker:
    """In-memory circuit breaker. Single-process safe (our architecture)."""

    def __init__(
        self,
        threshold: int | None = None,
        cooldown_seconds: int | None = None,
    ) -> None:
        self._threshold = threshold or settings.AGENT_BREAKER_THRESHOLD
        self._cooldown = cooldown_seconds or settings.AGENT_BREAKER_COOLDOWN_SECONDS
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        elapsed = time.time() - self._opened_at
        if elapsed >= self._cooldown:
            # Cooldown expired → auto-reset
            self._reset()
            return False
        return True

    def check(self) -> None:
        """Call before attempting the operation. Raises CircuitOpenError if open."""
        if self.is_open:
            remaining = int(self._cooldown - (time.time() - (self._opened_at or 0)))
            raise CircuitOpenError(
                f"Resume engine paused after {self._threshold} failures. "
                f"Retrying automatically in {remaining}s.",
                retry_after=remaining,
            )

    def record_success(self) -> None:
        """Record a successful call. Resets the failure counter."""
        if self._failure_count > 0:
            log.info("circuit_breaker_recovered", previous_failures=self._failure_count)
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed call. Opens the circuit if threshold reached."""
        self._failure_count += 1
        log.warning(
            "circuit_breaker_failure",
            count=self._failure_count,
            threshold=self._threshold,
        )
        if self._failure_count >= self._threshold:
            self._opened_at = time.time()
            log.error(
                "circuit_breaker_opened",
                cooldown_seconds=self._cooldown,
                failures=self._failure_count,
            )

    def _reset(self) -> None:
        log.info("circuit_breaker_reset_after_cooldown")
        self._failure_count = 0
        self._opened_at = None

    @property
    def state(self) -> str:
        return "open" if self.is_open else "closed"

    @property
    def failure_count(self) -> int:
        return self._failure_count


# Module-level singleton — shared across the single API process.
agent_breaker = CircuitBreaker()
