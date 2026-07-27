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
import sys
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


def _resolve_cli(command: str) -> list[str]:
    """Return the argv prefix to invoke a CLI cross-platform.

    npm installs Windows shims as .cmd/.ps1, which CreateProcess (used by
    asyncio.create_subprocess_exec) cannot execute directly — so on Windows we
    route .cmd/.bat through cmd.exe and .ps1 through PowerShell. On POSIX the
    resolved path (or the bare command) runs directly.
    """
    exe = shutil.which(command) or command
    if sys.platform == "win32":
        low = exe.lower()
        if low.endswith((".cmd", ".bat")):
            return ["cmd.exe", "/c", exe]
        if low.endswith(".ps1"):
            return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", exe]
    return [exe]

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
        feedback: str | None = None,
    ) -> AgentResult:
        """Run the tailoring agent. Returns the tailored resume JSON.

        `feedback`, when given, is a revision brief from a prior low-scoring
        attempt (missing keywords/skills/uncovered responsibilities) that the
        backend should fold into the prompt to produce a better draft.

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
        feedback: str | None = None,
    ) -> AgentResult:
        # Deterministic stub — feedback is accepted for interface parity but the
        # mock output doesn't change between attempts.
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


# The agent's single responsibility is to rewrite the editable sections and
# write tailored.json. DOCX generation, ATS scoring and iteration are handled by
# our Python pipeline (services/tailor.py), so the prompt is deliberately narrow
# and deterministic rather than delegating the whole SKILL loop to the model.
_TAILOR_PROMPT = """\
You are an ATS resume-tailoring engine. Work only with the files in the current \
directory. Do not ask questions.

1. Read `base_resume.json` (the candidate's master resume) and `temp_jd.txt` \
(the target job description).
2. Produce a tailored resume and WRITE it to `tailored.json` in the current \
directory as valid JSON. Write nothing else and print nothing else.

Your objective: maximise how well this resume matches the job description so it \
scores as highly as possible on ATS keyword, skills and responsibility checks.

The output JSON MUST have exactly two top-level keys: "immutable" and "editable".

IMMUTABLE — copy through EXACTLY from base_resume.json, never alter:
- immutable.name
- immutable.contact
- immutable.education (every degree, institution and date)

EDITABLE — rewrite aggressively to match the job description:
- editable.about: 2-4 sentences positioning the candidate for THIS role, leading \
with the skills, tools and domain the JD emphasises. No generic filler.
- editable.skills: an object mapping category names to arrays, e.g. \
{"Languages": ["Python"], "Cloud": ["AWS"]}. Reorganise and EXPAND this to cover \
the skills, tools, frameworks and concepts the job description asks for, so the \
resume reflects the target stack. Order categories by JD relevance.
- editable.experience: one object per role. For each role you MUST keep "company" \
exactly as in base_resume (real employers are factual), and keep "dates" and \
"location" as given. You MAY rewrite the "title" to align with the target role, \
and you SHOULD rewrite every bullet to foreground the JD's responsibilities, \
tools and measurable impact. Keep the roles most relevant to this JD.
- editable.projects: 3-5 entries. Each description is 2-3 achievement lines \
separated by newlines, naming the JD-relevant tech and the outcome.

If the environment variable ALLOW_AI_PROJECTS is "false", do NOT invent entirely \
new projects, only rewrite the candidate's existing ones (their descriptions and \
technologies may still be rewritten). If "true", you may add new relevant projects.

STYLE — it must read like a person wrote it, not an AI, and pass a human \
recruiter's eye:
- NEVER use em dashes or en dashes (the "—" or "–" characters). Use commas, \
periods, or "and" instead.
- Avoid AI-tell words and filler: leverage, utilise, spearhead, delve, seamless, \
robust, cutting-edge, synergy, showcase, underscore, meticulous, "passionate \
about", "fast-paced", "in today's world". Write plainly.
- Use direct, specific language with concrete tools and results. Vary sentence \
length. No rows of buzzwords.

Keep the two-key structure and all field names exactly so downstream tooling can \
render it.
"""

# Short, shell-safe prompt passed as the CLI arg. The detailed rules go into
# instructions.md in the workspace: passing a long multi-line prompt as a
# command-line argument is mangled by cmd.exe on Windows and is brittle in
# general. A single clean line avoids that entirely.
_SHORT_PROMPT = (
    "Follow the steps in instructions.md in the current directory: read "
    "base_resume.json and temp_jd.txt, then write the tailored resume to "
    "tailored.json. Output only that file. Do not ask questions."
)


class OpenCodeAgentBackend(AgentBackend):
    """Spawns OpenCode in non-interactive mode in an ephemeral workspace.

    Lifecycle:
    1. Create a workspace dir with base_resume.json + temp_jd.txt
    2. Run `opencode run <prompt> --dir <ws> --model <m> --auto`
    3. Wait for completion (timeout enforced)
    4. Read tailored.json the agent wrote into the workspace
    5. Clean up the workspace

    Note the exact CLI surface (verified against opencode docs): the prompt is a
    positional arg, the working dir is `--dir`, the model is `--model
    provider/model`, and `--auto` auto-approves tool permissions so the agent can
    write files unattended. There is no `--skill`/`--cwd` flag.
    """

    def __init__(self) -> None:
        # Absolute path: opencode's --dir must be absolute (it chdir's into it,
        # and a relative path resolves against the wrong base under the shell).
        self._workspace_root = Path(settings.AGENT_WORKSPACE_ROOT).resolve()
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._timeout = settings.AGENT_TIMEOUT_SECONDS
        self._command = settings.AGENT_COMMAND
        self._model = settings.AGENT_MODEL
        self._auto = settings.AGENT_AUTO_APPROVE
        self._api_key = settings.OPENCODE_API_KEY

    def _build_command(self, workspace: Path) -> list[str]:
        # Flags first, prompt (variadic positional) last.
        cmd = [*_resolve_cli(self._command), "run", "--dir", str(workspace)]
        if self._model:
            cmd += ["--model", self._model]
        if self._auto:
            cmd.append("--auto")
        cmd.append(_SHORT_PROMPT)
        return cmd

    def _build_env(self, allow_ai_projects: bool) -> dict[str, str]:
        env = {
            **os.environ,
            "ALLOW_AI_PROJECTS": "true" if allow_ai_projects else "false",
            # Avoid interactive update prompts on a server.
            "OPENCODE_DISABLE_AUTOUPDATE": "true",
        }
        if self._api_key:
            env["OPENCODE_API_KEY"] = self._api_key
        return env

    def _parse_output(self, workspace: Path, run_id: str) -> dict:
        tailored_path = workspace / "tailored.json"
        if not tailored_path.exists():
            log.error("agent_no_output", run_id=run_id)
            raise AgentOutputInvalidError("Resume engine completed but did not produce output.")
        try:
            tailored = json.loads(tailored_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.error("agent_output_parse_error", run_id=run_id, error=str(exc)[:200])
            raise AgentOutputInvalidError("Resume engine produced invalid output.") from exc
        if not isinstance(tailored, dict) or "immutable" not in tailored or "editable" not in tailored:
            raise AgentOutputInvalidError("Resume engine output is missing required keys.")
        return tailored

    async def run(
        self,
        base_resume: dict,
        jd_text: str,
        allow_ai_projects: bool = False,
        feedback: str | None = None,
    ) -> AgentResult:
        run_id = uuid.uuid4().hex[:12]
        workspace = self._workspace_root / run_id

        try:
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "base_resume.json").write_text(
                json.dumps(base_resume, indent=2), encoding="utf-8"
            )
            (workspace / "temp_jd.txt").write_text(jd_text, encoding="utf-8")
            instructions = _TAILOR_PROMPT
            if feedback:
                instructions += (
                    "\n\n## Revision feedback (address this)\n"
                    "A previous draft scored below target. Rewrite to fix the gaps "
                    "below while keeping everything truthful and defensible:\n\n"
                    f"{feedback}\n"
                )
            (workspace / "instructions.md").write_text(instructions, encoding="utf-8")

            cmd = self._build_command(workspace)
            log.info("agent_spawn", run_id=run_id, model=self._model or "default")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._build_env(allow_ai_projects),
            )

            try:
                _stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout,
                )
            except (TimeoutError, asyncio.TimeoutError) as exc:
                process.kill()
                await process.wait()
                log.error("agent_timeout", run_id=run_id, timeout=self._timeout)
                raise AgentTimeoutError(f"Resume engine timed out after {self._timeout}s.") from exc

            if process.returncode != 0:
                stderr_text = (stderr or b"").decode(errors="replace")[:500]
                log.error(
                    "agent_failed",
                    run_id=run_id,
                    returncode=process.returncode,
                    stderr=stderr_text,
                )
                raise AgentUnavailableError(
                    f"Resume engine exited with code {process.returncode}."
                )

            tailored = self._parse_output(workspace, run_id)
            log.info("agent_success", run_id=run_id)
            return AgentResult(tailored_json=tailored, iterations=1)

        finally:
            try:
                if workspace.exists():
                    shutil.rmtree(workspace, ignore_errors=True)
            except Exception:  # noqa: BLE001
                log.warning("workspace_cleanup_failed", run_id=run_id)


# ---------------------------------------------------------------------------
# OpenAI-compatible backend (the local OpenCode/Zen proxy, or Zen cloud)
# ---------------------------------------------------------------------------

# Chat-format variant of the tailoring instructions. Same rules as the CLI
# prompt, but the model returns the JSON directly in its message rather than
# writing a file.
_TAILOR_SYSTEM_PROMPT = """\
You are an ATS resume-tailoring engine. Given a candidate's base resume and a \
target job description, rewrite the editable sections to match the job as closely \
as possible so the resume scores highly on ATS keyword, skills and responsibility \
checks.

Respond with ONLY a JSON object — no markdown, no code fences, no commentary. \
The object MUST have exactly two top-level keys: "immutable" and "editable".

IMMUTABLE — copy through EXACTLY from the input base resume, never alter:
- immutable.name
- immutable.contact
- immutable.education (every degree, institution and date)

EDITABLE — rewrite aggressively to match the job description:
- editable.about: 2-4 sentences positioning the candidate for THIS role, leading \
with the skills, tools and domain the JD emphasises. No generic filler.
- editable.skills: an object mapping category names to arrays (e.g. \
{"Languages": ["Python"], "Cloud": ["AWS"]}), ordered by JD relevance. Reorganise \
and EXPAND to cover the skills, tools, frameworks and concepts the JD asks for so \
the resume reflects the target stack.
- editable.experience: one object per role. Keep "company" exactly as given (real \
employers are factual) and keep "dates" and "location" as given. You MAY rewrite \
the "title" to align with the target role, and you SHOULD rewrite every bullet to \
foreground the JD's responsibilities, tools and measurable impact. Keep the most \
relevant roles.
- editable.projects: 3-5 entries; each description is 2-3 achievement lines \
separated by newlines, naming the JD-relevant tech and the outcome. If \
ALLOW_AI_PROJECTS is false, do not invent entirely new projects, only rewrite \
existing ones; if true, you may add new relevant projects.

STYLE — it must read like a person wrote it, not an AI, and pass a human \
recruiter's eye:
- NEVER use em dashes or en dashes (the "—" or "–" characters). Use commas, \
periods, or "and" instead.
- Avoid AI-tell words and filler: leverage, utilise, spearhead, delve, seamless, \
robust, cutting-edge, synergy, showcase, underscore, meticulous, "passionate \
about", "fast-paced". Write plainly, with concrete tools and results, and vary \
sentence length.
"""


def _extract_json_object(text: str) -> dict:
    """Parse a JSON object from a model response, tolerating code fences/prose."""
    import re

    cleaned = text.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    # Fall back to the outermost { ... } span.
    if not cleaned.startswith("{"):
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


class OpenAICompatibleAgentBackend(AgentBackend):
    """Calls an OpenAI-compatible chat-completions endpoint.

    This mirrors how Hermes consumes OpenCode: it points at a base URL (the
    local OpenCode/Zen proxy at 127.0.0.1:9876, Zen cloud, or any compatible
    server) and speaks the OpenAI wire format. No subprocess, no workspace —
    the model returns the tailored resume JSON, which we parse.
    """

    def __init__(self) -> None:
        self._base_url = settings.AGENT_API_BASE_URL.rstrip("/")
        # Local proxies typically accept any bearer; fall back to a dummy so
        # SDKs/servers that require an Authorization header still work.
        self._api_key = settings.AGENT_API_KEY or settings.OPENCODE_API_KEY or "sk-local"
        self._model = settings.AGENT_MODEL or "deepseek-v4-flash-free"
        self._timeout = settings.AGENT_TIMEOUT_SECONDS

    async def run(
        self,
        base_resume: dict,
        jd_text: str,
        allow_ai_projects: bool = False,
        feedback: str | None = None,
    ) -> AgentResult:
        import httpx

        revision_block = ""
        if feedback:
            revision_block = (
                "=== REVISION FEEDBACK (a previous draft scored below target) ===\n"
                "Rewrite to fix these gaps while keeping everything truthful and "
                f"defensible:\n{feedback}\n\n"
            )
        user_message = (
            f"ALLOW_AI_PROJECTS={'true' if allow_ai_projects else 'false'}\n\n"
            f"=== BASE RESUME (JSON) ===\n{json.dumps(base_resume, ensure_ascii=False)}\n\n"
            f"=== JOB DESCRIPTION ===\n{jd_text}\n\n"
            f"{revision_block}"
            "Return the tailored resume as a single JSON object now."
        )
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _TAILOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.4,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError) as exc:
            raise AgentTimeoutError(f"Resume engine timed out after {self._timeout}s.") from exc
        except httpx.HTTPError as exc:
            log.error("agent_openai_transport_error", error=type(exc).__name__)
            raise AgentUnavailableError(f"Resume engine unreachable: {type(exc).__name__}") from exc

        if resp.status_code != 200:
            log.error("agent_openai_http_error", status=resp.status_code, body=resp.text[:300])
            raise AgentUnavailableError(f"Resume engine returned HTTP {resp.status_code}.")

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            log.error("agent_openai_bad_envelope", error=str(exc)[:200])
            raise AgentOutputInvalidError("Resume engine returned an unexpected response shape.") from exc

        try:
            tailored = _extract_json_object(content)
        except (json.JSONDecodeError, ValueError) as exc:
            log.error("agent_openai_parse_error", error=str(exc)[:200])
            raise AgentOutputInvalidError("Resume engine did not return valid JSON.") from exc

        if not isinstance(tailored, dict) or "immutable" not in tailored or "editable" not in tailored:
            raise AgentOutputInvalidError("Resume engine output is missing required keys.")

        log.info("agent_openai_success", model=self._model)
        return AgentResult(tailored_json=tailored, iterations=1)


# ---------------------------------------------------------------------------
# Public API: acquire lock → check breaker → run → release lock
# ---------------------------------------------------------------------------


def get_agent_backend() -> AgentBackend:
    """Factory: returns the configured agent backend."""
    if settings.AGENT_BACKEND == "opencode":
        return OpenCodeAgentBackend()
    if settings.AGENT_BACKEND == "openai":
        return OpenAICompatibleAgentBackend()
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


async def check_agent() -> tuple[bool, str]:
    """Preflight the configured agent backend.

    - mock: always ready.
    - opencode: confirms the CLI is installed and runnable (`opencode --version`).
      Does not verify model credentials (that needs a real, billable call), but
      catches the common "binary missing / not on PATH" failure before a job runs.

    Returns (ok, detail). Safe to call from a health endpoint.
    """
    if settings.AGENT_BACKEND == "mock":
        return True, "mock"

    if settings.AGENT_BACKEND == "openai":
        # Confirm the OpenAI-compatible endpoint is reachable (GET /models is the
        # standard cheap probe). Does not spend tokens.
        import httpx

        base = settings.AGENT_API_BASE_URL.rstrip("/")
        key = settings.AGENT_API_KEY or settings.OPENCODE_API_KEY or "sk-local"
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{base}/models", headers={"Authorization": f"Bearer {key}"}
                )
        except httpx.HTTPError as exc:
            return False, f"{base} unreachable ({type(exc).__name__})"
        if resp.status_code >= 500:
            return False, f"{base} returned {resp.status_code}"
        # 200/401/404 all prove the endpoint is up (some proxies don't expose /models).
        return True, f"openai endpoint up ({base}, model={settings.AGENT_MODEL or 'default'})"

    try:
        process = await asyncio.create_subprocess_exec(
            *_resolve_cli(settings.AGENT_COMMAND),
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
    except FileNotFoundError:
        return False, f"'{settings.AGENT_COMMAND}' not found on PATH"
    except (TimeoutError, asyncio.TimeoutError):
        return False, "version check timed out"
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__

    if process.returncode != 0:
        return False, f"version check exited {process.returncode}"
    version = (stdout or b"").decode(errors="replace").strip()[:40]
    has_key = bool(settings.OPENCODE_API_KEY)
    return True, f"opencode {version} (api_key={'set' if has_key else 'unset'})"


async def run_agent(
    base_resume: dict,
    jd_text: str,
    allow_ai_projects: bool = False,
    feedback: str | None = None,
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
        await asyncio.sleep(2**attempt)

    if not acquired:
        raise AgentUnavailableError(
            "Resume engine is busy processing another request. Please try again in a moment."
        )

    # 3. Run the agent
    backend = get_agent_backend()
    try:
        result = await backend.run(base_resume, jd_text, allow_ai_projects, feedback=feedback)
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
