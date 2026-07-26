"""Turn extracted resume text into structured profile fields for onboarding prefill.

Best-effort: the user always reviews/edits the result in the wizard before it is
saved. Uses the configured LLM backend (openai endpoint or the opencode CLI); for
the mock backend (and as a failure fallback) it does a lightweight regex pass so
the flow still works offline and in tests.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.profile import (
    EducationIn,
    ExperienceIn,
    ProjectIn,
    SkillCategoryIn,
)
from app.services.agent import _extract_json_object, _resolve_cli

log = get_logger(__name__)

_EXTRACT_INSTRUCTIONS = """\
You extract structured data from a resume. Respond with ONLY a JSON object — no \
markdown, no code fences, no commentary. Use exactly this schema:

{
  "full_name": string or null,
  "phone": string or null,
  "email": string or null,
  "educations": [{"degree": string, "institution": string, "dates": string or null}],
  "experiences": [{"title": string, "company": string, "location": string or null, "dates": string or null, "bullets": [string]}],
  "projects": [{"title": string, "description": string or null, "technologies": [string], "url": string or null}],
  "skills": [{"category": string, "items": [string]}]
}

Rules:
- Only include information actually present in the resume. Do not invent anything.
- Group skills into sensible categories (e.g. Languages, Frameworks, Tools).
- Keep experience bullets close to the original wording, lightly cleaned.
- If a section is absent, use null (scalars) or an empty array (lists).
"""


async def parse_resume(raw_text: str) -> dict:
    """Extract structured fields from resume text. Never raises — worst case it
    returns the heuristic result (or empties)."""
    text = (raw_text or "").strip()
    if not text:
        return _empty()

    try:
        if settings.AGENT_BACKEND == "openai":
            data = await _extract_via_openai(text)
        elif settings.AGENT_BACKEND == "opencode":
            data = await _extract_via_opencode(text)
        else:
            data = _extract_heuristic(text)
    except Exception:  # noqa: BLE001 - parsing must never fail the upload
        log.warning("resume_parse_failed", backend=settings.AGENT_BACKEND, exc_info=True)
        data = _extract_heuristic(text)

    return _sanitize(data)


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------


async def _extract_via_openai(text: str) -> dict:
    import httpx

    base = settings.AGENT_API_BASE_URL.rstrip("/")
    key = settings.AGENT_API_KEY or settings.OPENCODE_API_KEY or "sk-local"
    payload = {
        "model": settings.AGENT_MODEL or "deepseek-v4-flash-free",
        "messages": [
            {"role": "system", "content": _EXTRACT_INSTRUCTIONS},
            {"role": "user", "content": f"=== RESUME TEXT ===\n{text}\n\nReturn the JSON now."},
        ],
        "temperature": 0.1,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{base}/chat/completions", json=payload, headers={"Authorization": f"Bearer {key}"}
        )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _extract_json_object(content)


async def _extract_via_opencode(text: str) -> dict:
    workspace = Path(settings.AGENT_WORKSPACE_ROOT).resolve() / f"parse_{uuid.uuid4().hex[:12]}"
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "resume.txt").write_text(text, encoding="utf-8")
        (workspace / "instructions.md").write_text(_EXTRACT_INSTRUCTIONS, encoding="utf-8")

        cmd = [*_resolve_cli(settings.AGENT_COMMAND), "run", "--dir", str(workspace)]
        if settings.AGENT_MODEL:
            cmd += ["--model", settings.AGENT_MODEL]
        if settings.AGENT_AUTO_APPROVE:
            cmd.append("--auto")
        cmd.append(
            "Read resume.txt and instructions.md in the current directory, then write the "
            "extracted structured data to parsed.json following instructions.md. Output only "
            "that file. Do not ask questions."
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**_agent_env()},
        )
        await asyncio.wait_for(proc.communicate(), timeout=settings.AGENT_TIMEOUT_SECONDS)

        out = workspace / "parsed.json"
        if proc.returncode != 0 or not out.exists():
            raise RuntimeError(f"opencode parse failed (rc={proc.returncode})")
        return json.loads(out.read_text(encoding="utf-8"))
    finally:
        with __import__("contextlib").suppress(Exception):
            if workspace.exists():
                shutil.rmtree(workspace, ignore_errors=True)


def _agent_env() -> dict:
    import os

    env = {**os.environ, "OPENCODE_DISABLE_AUTOUPDATE": "true"}
    if settings.OPENCODE_API_KEY:
        env["OPENCODE_API_KEY"] = settings.OPENCODE_API_KEY
    return env


# ---------------------------------------------------------------------------
# Heuristic fallback (mock backend / offline / on LLM failure)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s\-().]{7,}\d)(?!\d)")


def _extract_heuristic(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = None
    phone = None
    if m := _EMAIL_RE.search(text):
        email = m.group(0)
    if m := _PHONE_RE.search(text):
        phone = m.group(1).strip()

    # Name: first non-empty line that isn't an email/phone/section header.
    full_name = None
    for ln in lines[:5]:
        if _EMAIL_RE.search(ln) or _PHONE_RE.search(ln):
            continue
        if len(ln) <= 60 and not ln.lower().startswith(("summary", "experience", "skills", "education")):
            full_name = ln
            break

    return {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "educations": [],
        "experiences": [],
        "projects": [],
        "skills": [],
    }


# ---------------------------------------------------------------------------
# Normalisation → valid schema items
# ---------------------------------------------------------------------------


def _empty() -> dict:
    return {
        "full_name": None,
        "phone": None,
        "email": None,
        "educations": [],
        "experiences": [],
        "projects": [],
        "skills": [],
    }


def _s(v: object, limit: int = 320) -> str | None:
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v[:limit] if v else None


def _sanitize(data: dict) -> dict:
    if not isinstance(data, dict):
        return _empty()

    def _items(key: str, model):
        out = []
        raw = data.get(key)
        if not isinstance(raw, list):
            return out
        for item in raw[:20]:
            if not isinstance(item, dict):
                continue
            try:
                out.append(model(**item))
            except Exception:  # noqa: BLE001 - skip malformed entries
                continue
        return out

    return {
        "full_name": _s(data.get("full_name"), 200),
        "phone": _s(data.get("phone"), 20),
        "email": _s(data.get("email"), 320),
        "educations": _items("educations", EducationIn),
        "experiences": _items("experiences", ExperienceIn),
        "projects": _items("projects", ProjectIn),
        "skills": _items("skills", SkillCategoryIn),
    }
