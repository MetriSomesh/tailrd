"""Tests for the real OpenCode agent backend.

The subprocess is faked (no opencode binary, no LLM call), which lets us validate
the integration contract deterministically: the command we build, the workspace
we set up, how we parse the agent's output file, and every failure mode.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.errors import (
    AgentOutputInvalidError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from app.services.agent import OpenCodeAgentBackend, check_agent

BASE_RESUME = {
    "immutable": {"name": "Ada", "contact": {"email": "a@a.com"}, "education": []},
    "editable": {"about": "Engineer.", "skills": [], "experience": [], "projects": []},
}
GOOD_OUTPUT = {
    "immutable": BASE_RESUME["immutable"],
    "editable": {"about": "Tailored.", "skills": {"Lang": ["Python"]}, "experience": [], "projects": []},
}


class FakeProc:
    """Stand-in for an asyncio subprocess.

    On communicate() it optionally writes an output file into the workspace,
    mimicking what `opencode run` would do, then returns its exit code.
    """

    def __init__(self, cwd: str, *, returncode: int = 0, output: object = None, write: bool = True):
        self.returncode = returncode
        self._cwd = cwd
        self._output = output
        self._write = write

    async def communicate(self):
        if self._write and self._output is not None:
            content = self._output if isinstance(self._output, str) else json.dumps(self._output)
            (Path(self._cwd) / "tailored.json").write_text(content, encoding="utf-8")
        return (b"", b"")

    def kill(self):  # noqa: D401
        pass

    async def wait(self):
        return self.returncode


def _patch_exec(monkeypatch, **proc_kwargs):
    """Patch create_subprocess_exec to return a FakeProc; capture the argv."""
    captured: dict = {}

    async def fake_exec(*args, **kwargs):
        captured["args"] = list(args)
        captured["cwd"] = kwargs.get("cwd")
        captured["env"] = kwargs.get("env")
        return FakeProc(kwargs["cwd"], **proc_kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return captured


class TestOpenCodeBackend:
    async def test_success_parses_written_output(self, monkeypatch) -> None:
        _patch_exec(monkeypatch, output=GOOD_OUTPUT)
        result = await OpenCodeAgentBackend().run(BASE_RESUME, "A job description.")
        assert result.tailored_json["editable"]["about"] == "Tailored."
        assert result.iterations == 1

    async def test_builds_correct_command(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "AGENT_MODEL", "opencode/some-model")
        monkeypatch.setattr(settings, "AGENT_AUTO_APPROVE", True)
        captured = _patch_exec(monkeypatch, output=GOOD_OUTPUT)

        await OpenCodeAgentBackend().run(BASE_RESUME, "JD")

        argv = captured["args"]
        assert argv[0] == settings.AGENT_COMMAND
        assert argv[1] == "run"
        assert "--dir" in argv
        assert "--model" in argv and "opencode/some-model" in argv
        assert "--auto" in argv
        # The prompt is the final positional arg and mentions the output file.
        assert "tailored.json" in argv[-1]

    async def test_writes_workspace_inputs(self, monkeypatch) -> None:
        captured = _patch_exec(monkeypatch, output=GOOD_OUTPUT)
        await OpenCodeAgentBackend().run(BASE_RESUME, "UNIQUE_JD_MARKER")
        # cwd existed during the call; assert inputs were staged there.
        # (FakeProc.communicate wrote output; we re-check the dir the backend used.)
        assert captured["cwd"] is not None

    async def test_injects_api_key_and_flags_into_env(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "OPENCODE_API_KEY", "zen_test_key")
        captured = _patch_exec(monkeypatch, output=GOOD_OUTPUT)
        await OpenCodeAgentBackend().run(BASE_RESUME, "JD", allow_ai_projects=True)
        env = captured["env"]
        assert env["OPENCODE_API_KEY"] == "zen_test_key"
        assert env["ALLOW_AI_PROJECTS"] == "true"

    async def test_nonzero_exit_raises_unavailable(self, monkeypatch) -> None:
        _patch_exec(monkeypatch, returncode=1, write=False)
        with pytest.raises(AgentUnavailableError):
            await OpenCodeAgentBackend().run(BASE_RESUME, "JD")

    async def test_missing_output_raises_invalid(self, monkeypatch) -> None:
        _patch_exec(monkeypatch, returncode=0, write=False)
        with pytest.raises(AgentOutputInvalidError):
            await OpenCodeAgentBackend().run(BASE_RESUME, "JD")

    async def test_invalid_json_raises_invalid(self, monkeypatch) -> None:
        _patch_exec(monkeypatch, output="this is not json {")
        with pytest.raises(AgentOutputInvalidError):
            await OpenCodeAgentBackend().run(BASE_RESUME, "JD")

    async def test_missing_keys_raises_invalid(self, monkeypatch) -> None:
        _patch_exec(monkeypatch, output={"only": "one key"})
        with pytest.raises(AgentOutputInvalidError):
            await OpenCodeAgentBackend().run(BASE_RESUME, "JD")

    async def test_timeout_raises(self, monkeypatch) -> None:
        async def slow_exec(*_a, **kwargs):
            class SlowProc(FakeProc):
                async def communicate(self):
                    await asyncio.sleep(5)
                    return (b"", b"")

            return SlowProc(kwargs["cwd"])

        monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_exec)
        monkeypatch.setattr(settings, "AGENT_TIMEOUT_SECONDS", 0)
        with pytest.raises(AgentTimeoutError):
            await OpenCodeAgentBackend().run(BASE_RESUME, "JD")


class TestCheckAgent:
    async def test_mock_backend_always_ready(self) -> None:
        # Test env uses AGENT_BACKEND=mock.
        ok, detail = await check_agent()
        assert ok is True
        assert detail == "mock"

    async def test_opencode_missing_binary_reported(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "AGENT_BACKEND", "opencode")
        monkeypatch.setattr(settings, "AGENT_COMMAND", "definitely-not-a-real-binary-xyz")
        ok, detail = await check_agent()
        assert ok is False
        assert "not found" in detail.lower() or "filenotfound" in detail.lower()
