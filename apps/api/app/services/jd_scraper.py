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

import asyncio
import html as html_lib
import ipaddress
import json
import re
import socket
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin, urlparse

from app.core.config import settings
from app.core.errors import JDScrapeError
from app.core.logging import get_logger

log = get_logger(__name__)

MAX_JD_CHARS = 15000
MIN_JD_CHARS = 120
MAX_HTML_BYTES = 4_000_000  # don't parse absurdly large pages
MAX_REDIRECTS = 5  # bound redirect chains; each hop is SSRF-revalidated

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


_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_from_html(html: str) -> str | None:
    """Run the extraction pipeline on rendered/served HTML; None if too thin."""
    structured = extract_jobposting_from_ld(_find_ld_json_blocks(html))
    if structured and len(structured) >= MIN_JD_CHARS:
        return structured
    text = extract_main_text(html)
    return text if len(text) >= MIN_JD_CHARS else None


# ---------------------------------------------------------------------------
# SSRF protection
#
# The JD URL is attacker-controlled and we fetch it server-side, so a naive
# fetch lets a user reach internal services (169.254.169.254 cloud metadata,
# 127.0.0.1, 10/8, etc.). We resolve the host and refuse any non-public address,
# and re-check on every redirect hop.
# ---------------------------------------------------------------------------


def _is_blocked_ip(ip_str: str) -> bool:
    """True if an IP is not a routable public address (or is unparseable)."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # can't reason about it -> block
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) so the IPv4 rules apply.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # covers 169.254.169.254 (cloud metadata)
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _host_is_blocked_literal(host: str) -> bool:
    """Cheap, DNS-free check: blocked IP literal or an obviously-local hostname."""
    if not host:
        return True
    h = host.strip("[]").lower()  # strip IPv6 brackets
    if h in ("localhost",) or h.endswith(".localhost") or h.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(h)
    except ValueError:
        return False  # a hostname; resolved+checked elsewhere
    return _is_blocked_ip(h)


async def _assert_public_url(url: str) -> None:
    """Raise JDScrapeError unless `url` is http(s) and resolves to public IPs only.

    Blocks if ANY resolved address is non-public, so a hostname that maps to both
    a public and a private IP can't be used to slip through.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise JDScrapeError("The job posting link must start with http:// or https://.")
    host = parsed.hostname
    if not host:
        raise JDScrapeError("That job posting link is not a valid URL.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise JDScrapeError("We couldn't resolve that job posting link.") from None

    for info in infos:
        ip_str = info[4][0]
        if _is_blocked_ip(ip_str):
            log.warning("jd_scrape_ssrf_blocked", host=host[:80], ip=ip_str)
            raise JDScrapeError(
                "That link points to a private or internal address, which isn't allowed."
            )


async def _scrape_with_http(url: str) -> str | None:
    """Tier 1: plain HTTP fetch. Returns None (not raises) on ordinary failures so
    the caller can try the browser fallback. Redirects are followed manually and
    each hop is SSRF-revalidated (a JDScrapeError from the guard propagates)."""
    import httpx

    resp = None
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=settings.JD_SCRAPE_TIMEOUT_SECONDS,
            headers=_HTTP_HEADERS,
        ) as client:
            current = url
            for _hop in range(MAX_REDIRECTS + 1):
                resp = await client.get(current)
                if not resp.is_redirect:
                    break
                location = resp.headers.get("location")
                if not location:
                    return None
                current = urljoin(current, location)
                await _assert_public_url(current)  # SSRF guard on the redirect target
            else:
                log.warning("jd_scrape_too_many_redirects", url=url[:120])
                return None
    except httpx.HTTPError as exc:
        log.warning("jd_scrape_http_error", url=url[:120], error=type(exc).__name__)
        return None

    if resp is None:
        return None
    if resp.status_code >= 400:
        log.warning("jd_scrape_http_status", url=url[:120], status=resp.status_code)
        return None

    content_type = resp.headers.get("content-type", "")
    if content_type and "html" not in content_type and "text" not in content_type:
        return None

    return _extract_from_html(resp.text[:MAX_HTML_BYTES])


async def _scrape_with_browser(url: str) -> str | None:
    """Tier 2: render with a headless browser (Playwright) for JS-heavy pages.

    Lazy-imports Playwright so it's only needed where the fallback is enabled.
    Returns None on any failure (including Playwright not being installed)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.warning("jd_scrape_browser_unavailable", detail="playwright not installed")
        return None

    timeout_ms = settings.JD_SCRAPE_TIMEOUT_SECONDS * 1000
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                context = await browser.new_context(
                    user_agent=_HTTP_HEADERS["User-Agent"],
                    viewport={"width": 1280, "height": 1600},
                )

                # SSRF guard for the browser: fully re-resolve navigation targets
                # (catches redirects to internal hosts) and cheaply block any
                # subresource pointed at a private IP literal / localhost.
                async def _guard(route: Any) -> None:
                    req = route.request
                    try:
                        if req.is_navigation_request():
                            await _assert_public_url(req.url)
                        elif _host_is_blocked_literal(urlparse(req.url).hostname or ""):
                            await route.abort()
                            return
                        await route.continue_()
                    except JDScrapeError:
                        await route.abort()
                    except Exception:  # noqa: BLE001 - never let the guard crash the render
                        await route.abort()

                await context.route("**/*", _guard)

                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:  # noqa: BLE001 - best-effort settle
                    pass
                await page.wait_for_timeout(800)
                html = await page.content()
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 - normalise all browser errors
        log.warning("jd_scrape_browser_error", url=url[:120], error=type(exc).__name__)
        return None

    return _extract_from_html(html)


async def scrape_jd(url: str) -> str:
    """Fetch the posting at `url` and return its job-description text.

    Tier 1 is a lightweight HTTP fetch (covers most ATS/job boards via JSON-LD).
    Tier 2 (optional, JD_SCRAPE_BROWSER_FALLBACK) renders JS-heavy SPAs with a
    headless browser. Raises JDScrapeError (refundable) if neither yields text.
    """
    if not isinstance(url, str) or not _URL_RE.match(url.strip()):
        raise JDScrapeError("The job posting link must start with http:// or https://.")
    url = url.strip()

    # Reject internal/private targets before we make any request (SSRF).
    await _assert_public_url(url)

    text = await _scrape_with_http(url)
    if text:
        log.info("jd_scrape_ok", url=url[:120], source="http", chars=len(text))
        return text

    if settings.JD_SCRAPE_BROWSER_FALLBACK:
        text = await _scrape_with_browser(url)
        if text:
            log.info("jd_scrape_ok", url=url[:120], source="browser", chars=len(text))
            return text

    raise JDScrapeError(
        "We couldn't read the job description from that page. It may load its content "
        "with JavaScript — try a direct link to the posting, or a job-board listing."
    )
