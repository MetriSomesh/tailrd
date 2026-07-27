"""Unit tests for the JD scraper's pure text-extraction helpers.

The browser orchestration (scrape_jd) is validated live; these cover the parsing
logic that turns rendered HTML / JSON-LD into clean job-description text.
"""

from __future__ import annotations

import json

from app.services.jd_scraper import (
    _clean_text,
    _strip_html,
    extract_jobposting_from_ld,
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
