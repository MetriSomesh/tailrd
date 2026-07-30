"""Tests for the OpenAI-compatible agent backend.

httpx is faked (no network, no LLM), validating the request we send, how we
parse the model's JSON reply (including code-fenced / prose-wrapped output),
and every failure mode.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import settings
from app.core.errors import (
    AgentOutputInvalidError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from app.services.agent import OpenAICompatibleAgentBackend, check_agent

BASE_RESUME = {
    "immutable": {"name": "Ada", "contact": {"email": "a@a.com"}, "education": []},
    "editable": {"about": "Engineer.", "skills": [], "experience": [], "projects": []},
}
GOOD_OUTPUT = {
    "immutable": BASE_RESUME["immutable"],
    "editable": {
        "about": "Tailored.",
        "skills": {"Lang": ["Python"]},
        "experience": [],
        "projects": [],
    },
}


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


class FakeResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


class FakeClient:
    def __init__(self, resp=None, exc=None, capture=None):
        self._resp = resp
        self._exc = exc
        self._capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, url, json=None, headers=None):
        if self._capture is not None:
            self._capture["url"] = url
            self._capture["json"] = json
            self._capture["headers"] = headers
        if self._exc:
            raise self._exc
        return self._resp

    async def get(self, url, headers=None):
        if self._exc:
            raise self._exc
        return self._resp


def _patch(monkeypatch, resp=None, exc=None, capture=None):
    def factory(*_a, **_k):
        return FakeClient(resp=resp, exc=exc, capture=capture)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


class TestOpenAIBackend:
    async def test_success_plain_json(self, monkeypatch) -> None:
        _patch(monkeypatch, resp=FakeResp(json_data=_completion(json.dumps(GOOD_OUTPUT))))
        result = await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD text")
        assert result.tailored_json["editable"]["about"] == "Tailored."

    async def test_success_code_fenced(self, monkeypatch) -> None:
        content = f"```json\n{json.dumps(GOOD_OUTPUT)}\n```"
        _patch(monkeypatch, resp=FakeResp(json_data=_completion(content)))
        result = await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")
        assert "editable" in result.tailored_json

    async def test_success_prose_wrapped(self, monkeypatch) -> None:
        content = f"Sure, here it is:\n{json.dumps(GOOD_OUTPUT)}\nHope that helps!"
        _patch(monkeypatch, resp=FakeResp(json_data=_completion(content)))
        result = await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")
        assert result.tailored_json["immutable"]["name"] == "Ada"

    async def test_builds_correct_request(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "AGENT_MODEL", "deepseek-v4-flash-free")
        monkeypatch.setattr(settings, "AGENT_API_BASE_URL", "http://127.0.0.1:9876/v1")
        capture: dict = {}
        _patch(
            monkeypatch,
            resp=FakeResp(json_data=_completion(json.dumps(GOOD_OUTPUT))),
            capture=capture,
        )

        await OpenAICompatibleAgentBackend().run(BASE_RESUME, "UNIQUE_JD", allow_ai_projects=True)

        assert capture["url"] == "http://127.0.0.1:9876/v1/chat/completions"
        assert capture["json"]["model"] == "deepseek-v4-flash-free"
        roles = [m["role"] for m in capture["json"]["messages"]]
        assert roles == ["system", "user"]
        assert "UNIQUE_JD" in capture["json"]["messages"][1]["content"]
        assert "ALLOW_AI_PROJECTS=true" in capture["json"]["messages"][1]["content"]
        assert capture["headers"]["Authorization"].startswith("Bearer ")

    async def test_http_500_raises_unavailable(self, monkeypatch) -> None:
        _patch(monkeypatch, resp=FakeResp(status_code=500, text="boom"))
        with pytest.raises(AgentUnavailableError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")

    async def test_transport_error_raises_unavailable(self, monkeypatch) -> None:
        _patch(monkeypatch, exc=httpx.ConnectError("refused"))
        with pytest.raises(AgentUnavailableError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")

    async def test_timeout_raises(self, monkeypatch) -> None:
        _patch(monkeypatch, exc=httpx.TimeoutException("slow"))
        with pytest.raises(AgentTimeoutError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")

    async def test_bad_envelope_raises_invalid(self, monkeypatch) -> None:
        _patch(monkeypatch, resp=FakeResp(json_data={"unexpected": True}))
        with pytest.raises(AgentOutputInvalidError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")

    async def test_non_json_content_raises_invalid(self, monkeypatch) -> None:
        _patch(monkeypatch, resp=FakeResp(json_data=_completion("I cannot help with that.")))
        with pytest.raises(AgentOutputInvalidError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")

    async def test_missing_keys_raises_invalid(self, monkeypatch) -> None:
        _patch(monkeypatch, resp=FakeResp(json_data=_completion(json.dumps({"only": 1}))))
        with pytest.raises(AgentOutputInvalidError):
            await OpenAICompatibleAgentBackend().run(BASE_RESUME, "JD")


class TestCheckAgentOpenAI:
    async def test_reachable_endpoint_ok(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "AGENT_BACKEND", "openai")
        _patch(monkeypatch, resp=FakeResp(status_code=200, json_data={"data": []}))
        ok, detail = await check_agent()
        assert ok is True
        assert "openai endpoint up" in detail

    async def test_unreachable_endpoint_reported(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "AGENT_BACKEND", "openai")
        _patch(monkeypatch, exc=httpx.ConnectError("refused"))
        ok, detail = await check_agent()
        assert ok is False
        assert "unreachable" in detail
