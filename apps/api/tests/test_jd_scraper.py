"""Unit tests for the JD scraper's pure text-extraction helpers.

The browser orchestration (scrape_jd) is validated live; these cover the parsing
logic that turns rendered HTML / JSON-LD into clean job-description text.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import settings
from app.core.errors import JDScrapeError
from app.services import jd_scraper
from app.services.jd_scraper import (
    _clean_text,
    _strip_html,
    extract_jobposting_from_ld,
    extract_main_text,
    scrape_jd,
)


class TestCleanText:
    def test_collapses_whitespace_and_blank_lines(self) -> None:
        raw = "  Senior   Engineer \n\n\n\n  Build   APIs \n \n"
        out = _clean_text(raw)
        # Inline whitespace collapses; blank lines are dropped.
        assert out == "Senior Engineer\nBuild APIs"

    def test_caps_length(self) -> None:
        assert len(_clean_text("x" * 20000)) == 15000


class TestStripHtml:
    def test_block_tags_become_line_breaks(self) -> None:
        html = "<p>Responsibilities</p><ul><li>Build APIs</li><li>Own uptime</li></ul>"
        out = _strip_html(html)
        assert "Responsibilities" in out
        assert "Build APIs" in out
        assert "Own uptime" in out
        # list items shouldn't run together
        assert "Build APIsOwn" not in out

    def test_drops_scripts_and_unescapes(self) -> None:
        html = "<script>evil()</script><p>Python &amp; FastAPI</p>"
        out = _strip_html(html)
        assert "evil" not in out
        assert "Python & FastAPI" in out


class TestExtractJobPostingFromLd:
    def test_extracts_description_and_title(self) -> None:
        block = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Backend Engineer",
                "hiringOrganization": {"@type": "Organization", "name": "Acme"},
                "description": "<p>Build scalable APIs with Python and FastAPI.</p>",
            }
        )
        out = extract_jobposting_from_ld([block])
        assert out is not None
        assert "Backend Engineer" in out
        assert "Acme" in out
        assert "Build scalable APIs with Python and FastAPI." in out

    def test_finds_jobposting_inside_graph(self) -> None:
        block = json.dumps(
            {
                "@graph": [
                    {"@type": "Organization", "name": "Acme"},
                    {"@type": "JobPosting", "description": "Own the backend platform."},
                ]
            }
        )
        out = extract_jobposting_from_ld([block])
        assert out == "Own the backend platform."

    def test_returns_none_without_jobposting(self) -> None:
        block = json.dumps({"@type": "WebPage", "name": "Careers"})
        assert extract_jobposting_from_ld([block]) is None

    def test_ignores_malformed_json(self) -> None:
        assert extract_jobposting_from_ld(["{not valid json", ""]) is None


class TestExtractMainText:
    def test_prefers_main_and_drops_boilerplate(self) -> None:
        html = (
            "<html><body><nav>Home About Careers</nav>"
            "<header>Logo</header>"
            "<main><h1>Backend Engineer</h1><p>Own the API platform.</p>"
            "<ul><li>Python</li><li>FastAPI</li></ul></main>"
            "<footer>© 2026</footer><script>track()</script></body></html>"
        )
        out = extract_main_text(html)
        assert "Backend Engineer" in out
        assert "Own the API platform." in out
        assert "Home About Careers" not in out
        assert "track()" not in out


# --- scrape_jd: httpx mocked so no network / browser is involved -------------


def _mock_get(monkeypatch, *, text="", status=200, content_type="text/html", exc=None):
    class FakeResp:
        def __init__(self):
            self.status_code = status
            self.text = text
            self.headers = {"content-type": content_type}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, _url):
            if exc:
                raise exc
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)


class TestScrapeJd:
    async def test_rejects_non_http_url(self) -> None:
        with pytest.raises(JDScrapeError):
            await scrape_jd("ftp://example.com/job")

    async def test_extracts_from_json_ld(self, monkeypatch) -> None:
        desc = (
            "<p>Build LLM agents, retrieval pipelines and backend APIs with Python and "
            "FastAPI. You will own evaluation, observability and guardrails, and ship "
            "production systems that serve real users at scale every single day.</p>"
        )
        html = (
            '<html><head><script type="application/ld+json">'
            + json.dumps({"@type": "JobPosting", "title": "AI Engineer", "description": desc})
            + "</script></head><body>shell</body></html>"
        )
        _mock_get(monkeypatch, text=html)
        out = await scrape_jd("https://boards.example.com/jobs/ai-engineer")
        assert "AI Engineer" in out
        assert "Build LLM agents" in out and "FastAPI" in out

    async def test_falls_back_to_main_text(self, monkeypatch) -> None:
        html = (
            "<html><body><nav>menu</nav><main><h1>Data Engineer</h1>"
            "<p>Design ETL pipelines and data models. Requires SQL, Python, Airflow "
            "and strong data warehousing fundamentals across large scale systems.</p>"
            "</main></body></html>"
        )
        _mock_get(monkeypatch, text=html)
        out = await scrape_jd("https://careers.example.com/data-engineer")
        assert "Data Engineer" in out
        assert "ETL pipelines" in out

    async def test_thin_spa_shell_raises(self, monkeypatch) -> None:
        _mock_get(monkeypatch, text="<html><body><div id='root'></div></body></html>")
        with pytest.raises(JDScrapeError):
            await scrape_jd("https://spa.example.com/job")

    async def test_http_error_status_raises(self, monkeypatch) -> None:
        _mock_get(monkeypatch, text="nope", status=404)
        with pytest.raises(JDScrapeError):
            await scrape_jd("https://example.com/missing")

    async def test_transport_error_raises(self, monkeypatch) -> None:
        _mock_get(monkeypatch, exc=httpx.ConnectError("refused"))
        with pytest.raises(JDScrapeError):
            await scrape_jd("https://unreachable.example.com/job")

    async def test_non_html_content_raises(self, monkeypatch) -> None:
        _mock_get(monkeypatch, text="{}", content_type="application/json")
        with pytest.raises(JDScrapeError):
            await scrape_jd("https://api.example.com/job.json")


class TestBrowserFallback:
    async def test_falls_back_to_browser_when_http_thin(self, monkeypatch) -> None:
        # HTTP returns a JS shell → thin → browser fallback (enabled) succeeds.
        _mock_get(monkeypatch, text="<html><body><div id='root'></div></body></html>")
        monkeypatch.setattr(settings, "JD_SCRAPE_BROWSER_FALLBACK", True)

        rendered = (
            "Senior Platform Engineer\n\nOwn Kubernetes, Terraform and CI/CD across a "
            "large multi-region fleet. Strong Go and distributed-systems background needed "
            "to keep the platform reliable and observable at scale."
        )

        async def _fake_browser(_url):
            return rendered

        monkeypatch.setattr(jd_scraper, "_scrape_with_browser", _fake_browser)

        out = await scrape_jd("https://spa.example.com/platform-engineer")
        assert out == rendered

    async def test_no_fallback_when_disabled(self, monkeypatch) -> None:
        _mock_get(monkeypatch, text="<html><body><div id='root'></div></body></html>")
        monkeypatch.setattr(settings, "JD_SCRAPE_BROWSER_FALLBACK", False)

        async def _boom(_url):
            raise AssertionError("browser fallback must not run when disabled")

        monkeypatch.setattr(jd_scraper, "_scrape_with_browser", _boom)

        with pytest.raises(JDScrapeError):
            await scrape_jd("https://spa.example.com/job")

    async def test_raises_when_both_tiers_thin(self, monkeypatch) -> None:
        _mock_get(monkeypatch, text="<html><body>shell</body></html>")
        monkeypatch.setattr(settings, "JD_SCRAPE_BROWSER_FALLBACK", True)

        async def _fake_browser(_url):
            return None  # browser also couldn't extract

        monkeypatch.setattr(jd_scraper, "_scrape_with_browser", _fake_browser)

        with pytest.raises(JDScrapeError):
            await scrape_jd("https://spa.example.com/job")
