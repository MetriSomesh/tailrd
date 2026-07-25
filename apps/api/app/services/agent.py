"""Agent runner: invokes Hermes/OpenCode to tailor a resume.

Two backends:
- mock: returns a deterministic tailored.json (dev/test, no subprocess)
- opencode: spawns the real agent in an ephemeral workspace, waits for output

Both backends are behind the same interface so the rest of the system never
knows which is active.

Concurrency control:
- Redis distributed lock (SETNX + TTL) ensures only one agent runs at a time
  across restarts. On a 1 GB host, two simultaneous agents = OOM.
- Circuit breaker rejects calls when the agent is known-broken.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.core.errors import (
    AgentOutputInvalidError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from app.core.logging import get_logger
from app.services.cache import get_redis
from app.services.circuit_breaker import agent_breaker

log = get_logger(__name__)


class AgentResult:
    """Result of a successful agent invocation."""

    def __init__(self, tailored_json: dict, iterations: int = 1) -> None:
        self.tailored_json = tailored_json
        self.iterations = iterations


class AgentBackend(ABC):
    @abstractmethod
    async def run(
        self,
        base_resume: dict,
        jd_text: str,
        allow_ai_projects: bool = False,
    ) -> AgentResult:
        """Run the tailoring agent. Returns the tailored resume JSON.

        Raises:
            AgentTimeoutError: if the agent exceeds the timeout
            AgentUnavailableError: if the agent cannot be started
            AgentOutputInvalidError: if the output doesn't parse
        """
        ...


# ---------------------------------------------------------------------------
# Mock backend (dev / test)
# ---------------------------------------------------------------------------


class MockAgentBackend(AgentBackend):
    """Returns a deterministic tailored.json without running any subprocess.

    Useful for:
    - Test suite (predictable, fast, no external deps)
    - Local dev when you want to test the pipeline without OpenCode installed
    """

    async def run(
        self,
        base_resume: dict,
        jd_text: str,
        allow_ai_projects: bool = False,
    ) -> AgentResult:
        # Simulate ~1s processing time
        await asyncio.sleep(0.1)

        editable = base_resume.get("editable", {})

        # Produce a minimally "tailored" version: add a hook line, categorize skills
        tailored = {
            "immutable": base_resume.get("immutable", {}),
            "editable": {
                "about": "Skilled at tackling ambiguous problem spaces and turning them into reliable, observable systems that ship. "
                + (editable.get("about") or "Full stack engineer."),
                "skills": editable.get("skills", []),
                "experience": editable.get("experience", [])[:2],
                "projects": editable.get("projects", []),
            },
        }

        return AgentResult(tailored_json=tailored, iterations=1)


# ---------------------------------------------------------------------------
# OpenCode backend (production)
# ---------------------------------------------------------------------------


class OpenCodeAgentBackend(AgentBackend):
    """Spawns OpenCode as a subprocess in an ephemeral workspace.

    Lifecycle:
    1. Create workspace dir with base_resume.json + temp_jd.txt
    2. Spawn `opencode run` with SKILL.md on the skills path
    3. Wait for completion (timeout enforced)
    4. Read tailored.json from the workspace
    5. Clean up workspace
    """

    def __init__(self) -> None:
        self._workspace_root = Path(settings.AGENT_WORKSPACE_ROOT)
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._skill_dir = Path(settings.AGENT_SKILL_DIR)
        self._timeout = settings.AGENT_TIMEOUT_SECONDS
        self._command = settings.AGENT_COMMAND

    async def run(
        self,
        base_resume: dict,
        jd_text: str,
        allow_ai_projects: bool = False,
    ) -> AgentResult:
        run_id = uuid.uuid4().hex[:12]
        workspace = self._workspace_root / run_id

        try:
            # Setup workspace
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "base_resume.json").write_text(
                json.dumps(base_resume, indent=2), encoding="utf-8"
            )
            (workspace / "temp_jd.txt").write_text(jd_text, encoding="utf-8")

            # Build the agent command
            # OpenCode's `run` command executes a skill non-interactively
            cmd = [
                self._command,
                "run",
                "--skill", "resume-tailor",
                "--cwd", str(workspace),
            ]

            log.info("agent_spawn", run_id=run_id, cmd=" ".join(cmd))

            # Spawn subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **os.environ,
                    "ALLOW_AI_PROJECTS": "true" if allow_ai_projects else "false",
                },
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout,
                )
            except TimeoutError as exc:
                # Kill the process group
                process.kill()
                await process.wait()
                log.error("agent_timeout", run_id=run_id, timeout=self._timeout)
                raise AgentTimeoutError(
                    f"Resume engine timed out after {self._timeout}s."
                ) from exc

            if process.returncode != 0:
                stderr_text = (stderr or b"").decode()[:500]
                log.error(
                    "agent_failed",
                    run_id=run_id,
                    returncode=process.returncode,
                    stderr=stderr_text,
                )
                raise AgentUnavailableError(
                    f"Resume engine exited with code {process.returncode}."
                )

            # Read the output
            tailored_path = workspace / "tailored.json"
            if not tailored_path.exists():
                log.error("agent_no_output", run_id=run_id)
                raise AgentOutputInvalidError(
                    "Resume engine completed but did not produce output."
                )

            try:
                tailored = json.loads(tailored_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                log.error("agent_output_parse_error", run_id=run_id, error=str(exc)[:200])
                raise AgentOutputInvalidError(
                    "Resume engine produced invalid output."
                ) from exc

            # Basic schema check
            if "immutable" not in tailored or "editable" not in tailored:
                raise AgentOutputInvalidError(
                    "Resume engine output is missing required keys."
                )

            log.info("agent_success", run_id=run_id)
            return AgentResult(tailored_json=tailored, iterations=1)

        finally:
            # Always clean up the workspace
            try:
                if workspace.exists():
                    shutil.rmtree(workspace, ignore_errors=True)
            except Exception:  # noqa: BLE001
                log.warning("workspace_cleanup_failed", run_id=run_id)


# ---------------------------------------------------------------------------
# Public API: acquire lock → check breaker → run → release lock
# ---------------------------------------------------------------------------


def get_agent_backend() -> AgentBackend:
    """Factory: returns the configured agent backend."""
    if settings.AGENT_BACKEND == "opencode":
        return OpenCodeAgentBackend()
    return MockAgentBackend()


async def acquire_agent_lock(wait_seconds: int = 10) -> bool:
    """Acquire the distributed agent lock via Redis SETNX.

    Returns True if acquired, False if another job holds it.
    The lock has a TTL so it auto-releases if the holder crashes.
    """
    try:
        redis = get_redis()
        acquired = await redis.set(
            settings.AGENT_LOCK_KEY,
            "locked",
            nx=True,
            ex=settings.AGENT_LOCK_TTL_SECONDS,
        )
        return bool(acquired)
    except Exception as exc:  # noqa: BLE001
        log.warning("agent_lock_acquire_failed", error=type(exc).__name__)
        # If Redis is down, allow the job to proceed (degraded mode).
        # The worst case is two simultaneous agents on a 1 GB host = OOM.
        # That's better than a permanently stuck queue.
        return True


async def release_agent_lock() -> None:
    """Release the distributed agent lock."""
    try:
        redis = get_redis()
        await redis.delete(settings.AGENT_LOCK_KEY)
    except Exception:  # noqa: BLE001
        log.warning("agent_lock_release_failed")


async def run_agent(
    base_resume: dict,
    jd_text: str,
    allow_ai_projects: bool = False,
) -> AgentResult:
    """Top-level entry point: breaker check → lock → run → unlock → report.

    This is what the worker calls. Handles all failure modes:
    - CircuitOpenError if breaker is open
    - AgentUnavailableError if lock can't be acquired after retries
    - AgentTimeoutError if the subprocess hangs
    - AgentOutputInvalidError if output is malformed
    """
    # 1. Circuit breaker gate
    agent_breaker.check()

    # 2. Acquire lock (with retry)
    acquired = False
    for attempt in range(3):
        acquired = await acquire_agent_lock()
        if acquired:
            break
        log.info("agent_lock_busy", attempt=attempt + 1)
        await asyncio.sleep(2 ** attempt)

    if not acquired:
        raise AgentUnavailableError(
            "Resume engine is busy processing another request. Please try again in a moment."
        )

    # 3. Run the agent
    backend = get_agent_backend()
    try:
        result = await backend.run(base_resume, jd_text, allow_ai_projects)
        agent_breaker.record_success()
        return result
    except (AgentTimeoutError, AgentUnavailableError, AgentOutputInvalidError):
        agent_breaker.record_failure()
        raise
    except Exception as exc:
        agent_breaker.record_failure()
        log.exception("agent_unexpected_error")
        raise AgentUnavailableError(f"Unexpected agent error: {type(exc).__name__}") from exc
    finally:
        await release_agent_lock()
