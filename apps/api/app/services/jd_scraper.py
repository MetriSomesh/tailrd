"""Scrape a job-posting URL into plain job-description text — lightweight, no browser.

Fetches the page over HTTP (httpx) and extracts the description from schema.org
JobPosting JSON-LD, which most ATS/job boards (Greenhouse, Lever, Workable, Ashby,
LinkedIn, Indeed, ...) embed in the served HTML for Google for Jobs. Falls back to
the page's readable main-content text.

No headless browser, so the memory/disk footprint is negligible. The tradeoff:
pure client-rendered SPAs that ship no JSON-LD and no server HTML can't be read —
those fail with a clear message so the user can paste a different link.

The pure text helpers are separated from the fetch so they can be unit-tested.
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
MAX_HTML_BYTES = 4_000_000  # don't parse absurdly large pages

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
# Boilerplate regions to drop before reading visible text.
_BOILERPLATE_RE = re.compile(
    r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form)\b[^>]*>.*?</\1>"
)
_MAIN_RE = re.compile(r"(?is)<(main|article)\b[^>]*>(.*?)</\1>")
_LD_JSON_RE = re.compile(
    r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
)
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
    """Turn an HTML fragment into readable text, preserving block breaks."""
    if not fragment:
        return ""
    without_scripts = _SCRIPT_STYLE_RE.sub(" ", fragment)
    with_breaks = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section)\s*>", "\n", without_scripts)
    with_breaks = re.sub(r"(?i)<br\s*/?>", "\n", with_breaks)
    text = _TAG_RE.sub(" ", with_breaks)
    return _clean_text(html_lib.unescape(text))


def _find_ld_json_blocks(html: str) -> list[str]:
    """Extract the raw contents of every <script type=application/ld+json> tag."""
    return [m.group(1).strip() for m in _LD_JSON_RE.finditer(html) if m.group(1).strip()]


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


def extract_main_text(html: str) -> str:
    """Best-effort readable text: drop boilerplate, prefer <main>/<article>."""
    stripped = _BOILERPLATE_RE.sub(" ", html)
    match = _MAIN_RE.search(stripped)
    region = match.group(2) if match else stripped
    text = _strip_html(region)
    # If <main>/<article> was tiny (e.g. a shell), fall back to the whole page.
    if len(text) < MIN_JD_CHARS and match:
        text = _strip_html(stripped)
    return text


async def scrape_jd(url: str) -> str:
    """Fetch the posting at `url` and return its job-description text.

    Raises JDScrapeError (refundable) if the page can't be fetched or yields too
    little text to be a real posting.
    """
    if not isinstance(url, str) or not _URL_RE.match(url.strip()):
        raise JDScrapeError("The job posting link must start with http:// or https://.")
    url = url.strip()

    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.JD_SCRAPE_TIMEOUT_SECONDS,
            headers=headers,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        log.warning("jd_scrape_fetch_error", url=url[:120], error=type(exc).__name__)
        raise JDScrapeError(
            "We couldn't open that job posting link. Check the URL and try again."
        ) from exc

    if resp.status_code >= 400:
        log.warning("jd_scrape_http_status", url=url[:120], status=resp.status_code)
        raise JDScrapeError(
            f"That link returned an error ({resp.status_code}). Check it opens the posting."
        )

    content_type = resp.headers.get("content-type", "")
    if content_type and "html" not in content_type and "text" not in content_type:
        raise JDScrapeError("That link isn't a web page we can read. Paste the posting's page URL.")

    html = resp.text[:MAX_HTML_BYTES]

    # 1. Prefer structured JSON-LD JobPosting.
    structured = extract_jobposting_from_ld(_find_ld_json_blocks(html))
    if structured and len(structured) >= MIN_JD_CHARS:
        log.info("jd_scrape_ok", url=url[:120], source="json-ld", chars=len(structured))
        return structured

    # 2. Fallback: readable main-content text.
    text = extract_main_text(html)
    if len(text) < MIN_JD_CHARS:
        raise JDScrapeError(
            "We couldn't read the job description from that page. It may load its content "
            "with JavaScript — try a direct link to the posting, or a job-board listing."
        )
    log.info("jd_scrape_ok", url=url[:120], source="text", chars=len(text))
    return text
