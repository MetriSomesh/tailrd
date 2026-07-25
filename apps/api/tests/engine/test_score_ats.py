"""Tests for score_ats.py — ATS scoring logic."""

import os

from app.engine.score_ats import (
    compute_skills_match,
    compute_keyword_match,
    compute_experience_relevance,
    extract_meaningful_words,
    flatten_skills,
)


FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return f.read()


class TestExtractMeaningfulWords:
    """Tests for the word extraction utility."""

    def test_removes_stop_words(self):
        words = extract_meaningful_words("the quick brown fox jumps over the lazy dog")
        assert 'the' not in words
        assert 'over' not in words
        assert 'quick' in words
        assert 'brown' in words

    def test_removes_short_words(self):
        words = extract_meaningful_words("I am a go to person for AI")
        assert 'am' not in words
        assert 'go' not in words

    def test_handles_empty_string(self):
        words = extract_meaningful_words("")
        assert words == []

    def test_preserves_tech_terms(self):
        words = extract_meaningful_words("Python Docker Redis FastAPI")
        assert 'python' in words
        assert 'docker' in words
        assert 'redis' in words


class TestFlattenSkills:
    """Tests for skills flattening logic."""

    def test_flattens_dict(self):
        skills_dict = {
            "Languages": ["Python", "TypeScript"],
            "Tools": ["Docker", "Git"]
        }
        result = flatten_skills(skills_dict)
        assert "Python" in result
        assert "Docker" in result
        assert len(result) == 4

    def test_passes_through_list(self):
        skills_list = ["Python", "TypeScript", "Docker"]
        result = flatten_skills(skills_list)
        assert result == skills_list

    def test_handles_empty_dict(self):
        assert flatten_skills({}) == []

    def test_handles_empty_list(self):
        assert flatten_skills([]) == []

    def test_handles_none(self):
        assert flatten_skills(None) == []

    def test_handles_non_list_values_in_dict(self):
        skills_dict = {"Languages": "Python"}  # Value is string, not list
        result = flatten_skills(skills_dict)
        assert "Python" in result


class TestComputeSkillsMatch:
    """Tests for skills matching against JD."""

    def test_perfect_match(self):
        jd = "We need Python, Docker, and Redis experience."
        resume_skills = ["Python", "Docker", "Redis", "JavaScript"]
        pct, matched, missing = compute_skills_match(jd, resume_skills)
        assert pct > 80
        assert len(missing) == 0 or len(matched) >= 3

    def test_no_match(self):
        jd = "We need Kubernetes, Terraform, and Helm experience."
        resume_skills = ["Python", "React", "MongoDB"]
        pct, matched, missing = compute_skills_match(jd, resume_skills)
        assert pct < 50
        assert len(missing) > 0

    def test_partial_match(self):
        jd = "We need Python, Docker, Redis, and Kubernetes."
        resume_skills = ["Python", "Docker", "JavaScript"]
        pct, matched, missing = compute_skills_match(jd, resume_skills)
        assert 30 < pct < 80
        assert 'python' in matched
        assert 'docker' in matched

    def test_empty_jd_returns_perfect_score(self):
        pct, matched, missing = compute_skills_match("No technical skills needed", [])
        # If JD has no recognizable skills, score should be 100
        assert pct == 100.0

    def test_case_insensitive_matching(self):
        jd = "Strong PYTHON and DOCKER skills required."
        resume_skills = ["python", "docker"]
        pct, matched, missing = compute_skills_match(jd, resume_skills)
        assert pct > 80


class TestComputeKeywordMatch:
    """Tests for keyword overlap scoring."""

    def test_full_overlap(self):
        jd = "Python developer with Docker and Redis experience"
        resume = "Experienced Python developer using Docker and Redis in production"
        pct, term_pct, missing, matched = compute_keyword_match(jd, resume)
        assert pct > 70

    def test_no_overlap(self):
        jd = "Kubernetes Terraform infrastructure engineer"
        resume = "React frontend developer building UI components"
        pct, term_pct, missing, matched = compute_keyword_match(jd, resume)
        assert pct < 50

    def test_empty_jd_returns_perfect(self):
        pct, term_pct, missing, matched = compute_keyword_match("", "Python Docker Redis")
        assert pct == 100.0

    def test_missing_keywords_populated(self):
        jd = "Python developer with Kubernetes and Terraform skills"
        resume = "Python developer with React skills"
        pct, term_pct, missing, matched = compute_keyword_match(jd, resume)
        assert len(missing) > 0


class TestComputeExperienceRelevance:
    """Tests for the responsibility-based experience scoring."""

    def test_relevant_experience_scores_high(self):
        jd = load_fixture('sample_jd_ai_engineer.txt')
        bullets = [
            "Built LLM-powered agents orchestrating multi-step legal document workflows processing 10,000+ pages weekly.",
            "Designed retrieval systems with 92% accuracy for document understanding and context management.",
            "Created eval benchmarks and guardrails measuring agent quality across 200+ test cases.",
            "Deployed backend APIs and services on AWS with Docker, achieving p95 latency under 800ms.",
        ]
        pct, covered, uncovered = compute_experience_relevance(jd, bullets)
        assert pct >= 30  # Should cover a meaningful portion of responsibilities

    def test_irrelevant_experience_scores_low(self):
        jd = load_fixture('sample_jd_ai_engineer.txt')
        bullets = [
            "Managed restaurant inventory and ordered supplies weekly.",
            "Trained 5 new cashiers on POS system usage.",
            "Handled customer complaints and resolved issues within 24 hours.",
        ]
        pct, covered, uncovered = compute_experience_relevance(jd, bullets)
        assert pct < 40

    def test_empty_bullets_scores_zero(self):
        jd = load_fixture('sample_jd_ai_engineer.txt')
        pct, covered, uncovered = compute_experience_relevance(jd, [])
        # Empty bullets can't cover responsibilities
        assert pct <= 10

    def test_empty_jd_returns_full_score(self):
        pct, covered, uncovered = compute_experience_relevance("", ["Built Python APIs"])
        assert pct == 100.0

    def test_returns_covered_and_uncovered_lists(self):
        jd = load_fixture('sample_jd_ai_engineer.txt')
        bullets = [
            "Built LLM-powered agents and multi-agent orchestration systems for document processing.",
        ]
        pct, covered, uncovered = compute_experience_relevance(jd, bullets)
        assert isinstance(covered, list)
        assert isinstance(uncovered, list)
        assert len(covered) + len(uncovered) > 0
