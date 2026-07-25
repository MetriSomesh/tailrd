"""Tests for validators.py — schema validation and safe file loading."""

import json
import os
import pytest

# Add project root to path
from app.engine.validators import validate_resume_schema, load_json_safe, load_text_safe


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestValidateResumeSchema:
    """Tests for validate_resume_schema()."""

    def test_valid_resume_returns_no_errors(self):
        path = os.path.join(FIXTURES, "valid_tailored.json")
        with open(path) as f:
            data = json.load(f)
        errors = validate_resume_schema(data)
        assert errors == []

    def test_missing_immutable_key(self):
        data = {"editable": {"about": "x", "skills": [], "experience": []}}
        errors = validate_resume_schema(data)
        assert any("immutable" in e for e in errors)

    def test_missing_editable_key(self):
        data = {"immutable": {"name": "X", "contact": {"email": "x"}, "education": []}}
        errors = validate_resume_schema(data)
        assert any("editable" in e for e in errors)

    def test_non_dict_root(self):
        errors = validate_resume_schema([1, 2, 3])
        assert errors == ["Root element must be a JSON object"]

    def test_missing_contact(self):
        data = {
            "immutable": {"name": "X", "education": []},
            "editable": {"about": "x", "skills": [], "experience": []},
        }
        errors = validate_resume_schema(data)
        assert any("contact" in e for e in errors)

    def test_missing_experience_bullets(self):
        data = {
            "immutable": {"name": "X", "contact": {"email": "x"}, "education": []},
            "editable": {
                "about": "x",
                "skills": [],
                "experience": [{"title": "T", "company": "C", "dates": "D"}],
            },
        }
        errors = validate_resume_schema(data)
        assert any("bullets" in e for e in errors)

    def test_empty_about_string(self):
        data = {
            "immutable": {"name": "X", "contact": {"email": "x"}, "education": []},
            "editable": {"about": "   ", "skills": [], "experience": []},
        }
        errors = validate_resume_schema(data)
        assert any("empty" in e.lower() for e in errors)

    def test_skills_as_dict_with_non_list_values(self):
        data = {
            "immutable": {"name": "X", "contact": {"email": "x"}, "education": []},
            "editable": {
                "about": "test",
                "skills": {"Languages": "python"},  # should be a list
                "experience": [],
            },
        }
        errors = validate_resume_schema(data)
        assert any("list" in e for e in errors)

    def test_malformed_fixture(self):
        path = os.path.join(FIXTURES, "malformed_tailored.json")
        with open(path) as f:
            data = json.load(f)
        errors = validate_resume_schema(data)
        # Should have multiple errors
        assert len(errors) >= 2

    def test_minimal_valid_resume(self):
        path = os.path.join(FIXTURES, "minimal_tailored.json")
        with open(path) as f:
            data = json.load(f)
        errors = validate_resume_schema(data)
        assert errors == []


class TestLoadJsonSafe:
    """Tests for load_json_safe() error handling."""

    def test_nonexistent_file_exits(self):
        with pytest.raises(SystemExit):
            load_json_safe("/nonexistent/path/file.json")

    def test_valid_file_loads(self):
        path = os.path.join(FIXTURES, "valid_tailored.json")
        data = load_json_safe(path)
        assert data["immutable"]["name"] == "Test Candidate"

    def test_invalid_json_exits(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json content")
        with pytest.raises(SystemExit):
            load_json_safe(str(bad_file))


class TestLoadTextSafe:
    """Tests for load_text_safe() error handling."""

    def test_nonexistent_file_exits(self):
        with pytest.raises(SystemExit):
            load_text_safe("/nonexistent/path/file.txt")

    def test_valid_file_loads(self):
        path = os.path.join(FIXTURES, "sample_jd_ai_engineer.txt")
        text = load_text_safe(path)
        assert "Lexi" in text
        assert len(text) > 100
