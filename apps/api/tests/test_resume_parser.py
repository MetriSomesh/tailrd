"""Tests for resume parsing (heuristic path + the parse-resume endpoint).

Tests run with AGENT_BACKEND=mock, so parse_resume uses the regex heuristic —
deterministic, no LLM.
"""

from __future__ import annotations

import io

from docx import Document
from httpx import AsyncClient

RESUME_TEXT = """Jane Developer
jane.dev@example.com | +1 415 555 0100
Summary
Backend engineer with FastAPI experience.
"""


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestHeuristicParse:
    async def test_extracts_contact_fields(self) -> None:
        from app.services.resume_parser import parse_resume

        result = await parse_resume(RESUME_TEXT)
        assert result["email"] == "jane.dev@example.com"
        assert result["phone"] is not None
        assert result["full_name"] == "Jane Developer"

    async def test_empty_text_is_safe(self) -> None:
        from app.services.resume_parser import parse_resume

        r = await parse_resume("   ")
        assert r["email"] is None
        assert r["experiences"] == []

    async def test_llm_failure_falls_back_to_heuristic(self, monkeypatch) -> None:
        """If the LLM extractor errors/times out, we still return heuristic fields
        rather than failing the upload (this is what prevents the 500)."""
        from app.core.config import settings
        from app.services import resume_parser

        monkeypatch.setattr(settings, "AGENT_BACKEND", "opencode")

        async def _boom(_text):
            raise RuntimeError("opencode parse timed out")

        monkeypatch.setattr(resume_parser, "_extract_via_opencode", _boom)

        result = await resume_parser.parse_resume(RESUME_TEXT)
        # Fell back to heuristic — contact fields still extracted, no exception.
        assert result["email"] == "jane.dev@example.com"
        assert result["full_name"] == "Jane Developer"

    async def test_sanitize_drops_malformed_items(self) -> None:
        from app.services.resume_parser import _sanitize

        data = {
            "full_name": "X",
            "educations": [
                {"degree": "BS CS", "institution": "State U"},
                {"degree": "missing institution"},  # invalid → dropped
            ],
            "experiences": [{"title": "SWE", "company": "Acme"}],
            "skills": [{"category": "Languages", "items": ["Python"]}, {"nope": 1}],
            "projects": "not a list",
        }
        s = _sanitize(data)
        assert len(s["educations"]) == 1
        assert len(s["experiences"]) == 1
        assert len(s["skills"]) == 1
        assert s["projects"] == []


class TestParseResumeEndpoint:
    async def test_upload_docx_returns_structured_fields(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "parse@test.com", "password": "strongPass123!", "name": "Parse"},
        )
        files = {
            "file": (
                "resume.docx",
                _docx_bytes(RESUME_TEXT),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        r = await client.post("/api/v1/profile/parse-resume", files=files)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "jane.dev@example.com"
        assert body["full_name"] == "Jane Developer"
        assert body["raw_text"]

    async def test_rejects_unsupported_type(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "parse2@test.com", "password": "strongPass123!", "name": "P2"},
        )
        files = {"file": ("notes.txt", b"hello", "text/plain")}
        r = await client.post("/api/v1/profile/parse-resume", files=files)
        assert r.status_code == 415

    async def test_requires_auth(self, client: AsyncClient) -> None:
        files = {"file": ("resume.docx", _docx_bytes(RESUME_TEXT),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = await client.post("/api/v1/profile/parse-resume", files=files)
        assert r.status_code in (401, 403)
