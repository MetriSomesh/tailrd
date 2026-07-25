"""Tests for the agent runner: mock backend, circuit breaker, lock, run_agent."""

from __future__ import annotations

import time

import pytest

from app.services.agent import (
    AgentResult,
    MockAgentBackend,
    acquire_agent_lock,
    release_agent_lock,
    run_agent,
)
from app.services.circuit_breaker import CircuitBreaker, agent_breaker

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=60)
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"

    def test_check_raises_when_open(self) -> None:
        from app.core.errors import CircuitOpenError

        cb = CircuitBreaker(threshold=2, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        with pytest.raises(CircuitOpenError):
            cb.check()

    def test_resets_after_cooldown(self) -> None:
        cb = CircuitBreaker(threshold=2, cooldown_seconds=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        time.sleep(1.1)
        assert cb.state == "closed"

    def test_success_resets_counter(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_check_passes_when_closed(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=60)
        cb.check()  # should not raise


# ---------------------------------------------------------------------------
# Mock Backend
# ---------------------------------------------------------------------------


class TestMockBackend:
    async def test_returns_tailored_json(self) -> None:
        backend = MockAgentBackend()
        base = {
            "immutable": {"name": "Test", "contact": {"phone": "123", "email": "t@t.com"}, "education": []},
            "editable": {
                "about": "Engineer.",
                "skills": ["Python", "React"],
                "experience": [
                    {"title": "SWE", "company": "X", "dates": "2024", "bullets": ["Did stuff."]},
                    {"title": "Jr", "company": "Y", "dates": "2023", "bullets": ["Other."]},
                    {"title": "Intern", "company": "Z", "dates": "2022", "bullets": ["Learning."]},
                ],
                "projects": [],
            },
        }
        result = await backend.run(base, "Some JD text about Python and APIs.")
        assert isinstance(result, AgentResult)
        assert "immutable" in result.tailored_json
        assert "editable" in result.tailored_json
        # Should keep only 2 experiences
        assert len(result.tailored_json["editable"]["experience"]) == 2
        # Summary should start with the hook line
        assert result.tailored_json["editable"]["about"].startswith("Skilled at tackling")

    async def test_handles_empty_resume(self) -> None:
        backend = MockAgentBackend()
        base = {"immutable": {}, "editable": {}}
        result = await backend.run(base, "Any JD.")
        assert result.tailored_json is not None


# ---------------------------------------------------------------------------
# Agent Lock
# ---------------------------------------------------------------------------


class TestAgentLock:
    async def test_acquire_and_release(self) -> None:
        # Ensure clean state
        await release_agent_lock()
        assert await acquire_agent_lock() is True
        # Second acquire should fail (lock held)
        assert await acquire_agent_lock() is False
        # Release
        await release_agent_lock()
        # Now can acquire again
        assert await acquire_agent_lock() is True
        await release_agent_lock()


# ---------------------------------------------------------------------------
# run_agent (integration)
# ---------------------------------------------------------------------------


class TestRunAgent:
    async def test_succeeds_with_mock_backend(self) -> None:
        # Reset breaker state
        agent_breaker._failure_count = 0
        agent_breaker._opened_at = None
        await release_agent_lock()

        base = {
            "immutable": {"name": "X", "contact": {"email": "x@x.com"}, "education": []},
            "editable": {"about": "Hi.", "skills": [], "experience": [], "projects": []},
        }
        result = await run_agent(base, "JD text")
        assert result.tailored_json["immutable"]["name"] == "X"
        assert result.iterations == 1

    async def test_rejects_when_breaker_open(self) -> None:
        from app.core.errors import CircuitOpenError

        agent_breaker._failure_count = 0
        agent_breaker._opened_at = None
        # Force breaker open
        for _ in range(5):
            agent_breaker.record_failure()

        with pytest.raises(CircuitOpenError):
            await run_agent({}, "JD")

        # Reset
        agent_breaker._failure_count = 0
        agent_breaker._opened_at = None

    async def test_releases_lock_on_success(self) -> None:
        agent_breaker._failure_count = 0
        agent_breaker._opened_at = None
        await release_agent_lock()

        base = {
            "immutable": {},
            "editable": {"about": "X", "skills": [], "experience": [], "projects": []},
        }
        await run_agent(base, "JD")
        # Lock should be released — can acquire immediately
        assert await acquire_agent_lock() is True
        await release_agent_lock()
