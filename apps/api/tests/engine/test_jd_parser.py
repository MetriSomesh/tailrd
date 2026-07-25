"""Tests for jd_parser.py — JD analysis, skill extraction, and section parsing."""

import os

from app.engine.jd_parser import (
    extract_skills_from_jd,
    extract_sections,
    extract_responsibilities,
    extract_required_qualifications,
    analyze_jd,
)


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


class TestExtractSkillsFromJd:
    """Tests for dynamic skill extraction."""

    def test_ai_engineer_extracts_python(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        skills = extract_skills_from_jd(jd)
        assert "python" in skills

    def test_ai_engineer_extracts_docker(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        skills = extract_skills_from_jd(jd)
        assert "docker" in skills

    def test_ai_engineer_extracts_redis(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        skills = extract_skills_from_jd(jd)
        assert "redis" in skills

    def test_frontend_extracts_react(self):
        jd = load_fixture("sample_jd_frontend.txt")
        skills = extract_skills_from_jd(jd)
        assert "react" in skills

    def test_frontend_extracts_typescript(self):
        jd = load_fixture("sample_jd_frontend.txt")
        skills = extract_skills_from_jd(jd)
        assert "typescript" in skills

    def test_frontend_extracts_next_js(self):
        jd = load_fixture("sample_jd_frontend.txt")
        skills = extract_skills_from_jd(jd)
        assert "next.js" in skills or "nextjs" in skills

    def test_frontend_does_not_extract_unmentioned_skills(self):
        jd = load_fixture("sample_jd_frontend.txt")
        skills = extract_skills_from_jd(jd)
        # These shouldn't be in a frontend JD
        assert "kubernetes" not in skills
        assert "pytorch" not in skills

    def test_empty_jd_returns_empty_set(self):
        skills = extract_skills_from_jd("")
        assert skills == set()

    def test_extracts_multi_word_terms(self):
        jd = "We need experience with machine learning and React Native development."
        skills = extract_skills_from_jd(jd)
        assert "machine learning" in skills
        assert "react native" in skills


class TestExtractSections:
    """Tests for JD section parsing."""

    def test_ai_jd_has_responsibilities(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        sections = extract_sections(jd)
        # Should find at least a responsibilities section
        section_keys_lower = [k.lower() for k in sections.keys()]
        assert any("responsibilit" in k for k in section_keys_lower)

    def test_frontend_jd_has_requirements(self):
        jd = load_fixture("sample_jd_frontend.txt")
        sections = extract_sections(jd)
        section_keys_lower = [k.lower() for k in sections.keys()]
        assert any("requirement" in k for k in section_keys_lower)

    def test_empty_jd_returns_general_only(self):
        sections = extract_sections("")
        assert "general" in sections

    def test_sections_contain_content(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        sections = extract_sections(jd)
        # At least one section should have content
        total_lines = sum(len(v) for v in sections.values())
        assert total_lines > 0


class TestExtractResponsibilities:
    """Tests for responsibility extraction."""

    def test_ai_jd_finds_responsibilities(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        responsibilities = extract_responsibilities(jd)
        assert len(responsibilities) >= 3

    def test_responsibilities_contain_llm_related(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        responsibilities = extract_responsibilities(jd)
        combined = " ".join(responsibilities).lower()
        assert "llm" in combined or "agent" in combined

    def test_frontend_jd_finds_responsibilities(self):
        jd = load_fixture("sample_jd_frontend.txt")
        responsibilities = extract_responsibilities(jd)
        assert len(responsibilities) >= 3

    def test_empty_jd_returns_empty_list(self):
        responsibilities = extract_responsibilities("")
        assert responsibilities == []


class TestExtractRequiredQualifications:
    """Tests for qualification extraction."""

    def test_ai_jd_finds_qualifications(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        quals = extract_required_qualifications(jd)
        assert len(quals) >= 3

    def test_frontend_jd_finds_requirements(self):
        jd = load_fixture("sample_jd_frontend.txt")
        quals = extract_required_qualifications(jd)
        assert len(quals) >= 3


class TestAnalyzeJd:
    """Tests for the full analyze_jd() function."""

    def test_returns_all_keys(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        result = analyze_jd(jd)
        assert "skills" in result
        assert "responsibilities" in result
        assert "qualifications" in result
        assert "sections" in result

    def test_skills_is_a_set(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        result = analyze_jd(jd)
        assert isinstance(result["skills"], set)

    def test_responsibilities_is_a_list(self):
        jd = load_fixture("sample_jd_ai_engineer.txt")
        result = analyze_jd(jd)
        assert isinstance(result["responsibilities"], list)
