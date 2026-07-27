"""Scrape a job-posting URL into plain job-description text.

Uses a headless Chromium (Playwright) so JavaScript-rendered postings (Greenhouse,
Lever, Workday, custom SPAs) work, not just static HTML. Extraction prefers the
schema.org JobPosting JSON-LD `description` (clean, structured), and falls back to
the main content's visible text.

The pure text-processing helpers are separated from the browser orchestration so
they can be unit-tested without launching a browser.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from collections.abc import Iterator
from typing import Any

from app.core.config import settings
from app.core.errors import JDScrapeError
from app.core.logging import get_logger

log = get_logger(__name__)

MAX_JD_CHARS = 15000
MIN_JD_CHARS = 120

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
_INLINE_WS_RE = re.compile(r"[ \t\u00a0]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _clean_text(text: str) -> str:
    """Collapse whitespace, drop blank lines, cap length."""
    if not text:
        return ""
    lines = [_INLINE_WS_RE.sub(" ", ln).strip() for ln in text.splitlines()]
    joined = "\n".join(ln for ln in lines if ln)
    joined = _MULTI_NL_RE.sub("\n\n", joined)
    return joined.strip()[:MAX_JD_CHARS]


def _strip_html(fragment: str) -> str:
    """Turn an HTML fragment (e.g. a JSON-LD description) into readable text."""
    if not fragment:
        return ""
    without_scripts = _SCRIPT_STYLE_RE.sub(" ", fragment)
    # Preserve block breaks so bullet lists don't run together.
    with_breaks = re.sub(r"(?i)</(p|div|li|h[1-6]|br)\s*>", "\n", without_scripts)
    with_breaks = re.sub(r"(?i)<br\s*/?>", "\n", with_breaks)
    text = _TAG_RE.sub(" ", with_breaks)
    return _clean_text(html_lib.unescape(text))


def _iter_ld_nodes(data: Any) -> Iterator[dict]:
    """Yield every dict node in a JSON-LD document, following @graph and lists."""
    if isinstance(data, dict):
        yield data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for node in graph:
                yield from _iter_ld_nodes(node)
    elif isinstance(data, list):
        for node in data:
            yield from _iter_ld_nodes(node)


def _is_jobposting(node: dict) -> bool:
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(str(x).lower() == "jobposting" for x in types)


def extract_jobposting_from_ld(ld_blocks: list[str]) -> str | None:
    """Find a JobPosting in JSON-LD blocks and return its title + description text."""
    for block in ld_blocks:
        if not block:
            continue
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        for node in _iter_ld_nodes(data):
            if not isinstance(node, dict) or not _is_jobposting(node):
                continue
            desc = node.get("description")
            if not isinstance(desc, str) or not desc.strip():
                continue
            title = node.get("title")
            org = node.get("hiringOrganization")
            org_name = org.get("name") if isinstance(org, dict) else None
            header = " — ".join(x for x in (title, org_name) if isinstance(x, str) and x.strip())
            body = _strip_html(desc)
            return _clean_text(f"{header}\n\n{body}" if header else body)
    return None


async def scrape_jd(url: str) -> str:
    """Render the posting at `url` and return its job-description text.

    Raises JDScrapeError (refundable) if the page can't be read or yields too
    little text to be a real posting.
    """
    if not isinstance(url, str) or not _URL_RE.match(url.strip()):
        raise JDScrapeError("The job posting link must start with http:// or https://.")
    url = url.strip()

    from playwright.async_api import async_playwright

    timeout_ms = settings.JD_SCRAPE_TIMEOUT_SECONDS * 1000

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 1600},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                # Give SPAs a moment to render the posting.
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:  # noqa: BLE001 - networkidle is best-effort
                    pass
                await page.wait_for_timeout(800)

                # 1. Prefer structured JSON-LD JobPosting.
                ld_blocks = await page.eval_on_selector_all(
                    'script[type="application/ld+json"]',
                    "els => els.map(e => e.textContent)",
                )
                structured = extract_jobposting_from_ld([b for b in ld_blocks if b])
                if structured and len(structured) >= MIN_JD_CHARS:
                    log.info("jd_scrape_ok", url=url[:120], source="json-ld", chars=len(structured))
                    return structured

                # 2. Fallback: visible text of the main content region.
                text = ""
                for selector in ("main", "article", "[role=main]", "#content", "body"):
                    try:
                        el = await page.query_selector(selector)
                        if el:
                            candidate = _clean_text(await el.inner_text())
                            if len(candidate) > len(text):
                                text = candidate
                            if len(text) >= MIN_JD_CHARS and selector != "body":
                                break
                    except Exception:  # noqa: BLE001
                        continue

                if len(text) < MIN_JD_CHARS:
                    raise JDScrapeError(
                        "We couldn't read the job description from that page. "
                        "Check the link opens the posting directly."
                    )
                log.info("jd_scrape_ok", url=url[:120], source="text", chars=len(text))
                return text
            finally:
                await browser.close()
    except JDScrapeError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalise all browser errors
        log.warning("jd_scrape_failed", url=url[:120], error=type(exc).__name__, detail=str(exc)[:200])
        raise JDScrapeError(
            "We couldn't open that job posting link. Check the URL and try again."
        ) from exc
