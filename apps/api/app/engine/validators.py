#!/usr/bin/env python3
"""Schema validation for resume-tailor JSON files."""

import json
import os
import sys


def load_json_safe(path):
    """Load a JSON file with proper error handling.

    Returns:
        dict: Parsed JSON data.

    Raises:
        SystemExit: On file not found or invalid JSON.
    """
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"ERROR: Permission denied reading: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def load_text_safe(path):
    """Load a text file with proper error handling.

    Returns:
        str: File content.

    Raises:
        SystemExit: On file not found or read error.
    """
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            print(f"WARNING: File is empty: {path}", file=sys.stderr)
        return content
    except PermissionError:
        print(f"ERROR: Permission denied reading: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_resume_schema(data):
    """Validate the structure of a tailored resume JSON.

    Args:
        data: Parsed JSON dict.

    Returns:
        list: List of error strings. Empty list means valid.
    """
    errors = []

    # Top-level keys
    if not isinstance(data, dict):
        return ["Root element must be a JSON object"]

    if 'immutable' not in data:
        errors.append("Missing required key: 'immutable'")
    if 'editable' not in data:
        errors.append("Missing required key: 'editable'")

    if errors:
        return errors  # Can't validate further without these

    # Validate immutable section
    immutable = data['immutable']
    if not isinstance(immutable, dict):
        errors.append("'immutable' must be an object")
    else:
        if 'name' not in immutable:
            errors.append("Missing 'immutable.name'")
        if 'contact' not in immutable:
            errors.append("Missing 'immutable.contact'")
        elif not isinstance(immutable['contact'], dict):
            errors.append("'immutable.contact' must be an object")
        else:
            if 'email' not in immutable['contact']:
                errors.append("Missing 'immutable.contact.email'")
        if 'education' not in immutable:
            errors.append("Missing 'immutable.education'")
        elif not isinstance(immutable['education'], list):
            errors.append("'immutable.education' must be an array")

    # Validate editable section
    editable = data['editable']
    if not isinstance(editable, dict):
        errors.append("'editable' must be an object")
    else:
        # About
        if 'about' not in editable:
            errors.append("Missing 'editable.about'")
        elif not isinstance(editable['about'], str):
            errors.append("'editable.about' must be a string")
        elif len(editable['about'].strip()) == 0:
            errors.append("'editable.about' is empty")

        # Skills
        if 'skills' not in editable:
            errors.append("Missing 'editable.skills'")
        elif not isinstance(editable['skills'], (list, dict)):
            errors.append("'editable.skills' must be a list or categorized dict")
        elif isinstance(editable['skills'], dict):
            for cat, items in editable['skills'].items():
                if not isinstance(items, list):
                    errors.append(f"Skills category '{cat}' must contain a list")

        # Experience
        if 'experience' not in editable:
            errors.append("Missing 'editable.experience'")
        elif not isinstance(editable['experience'], list):
            errors.append("'editable.experience' must be an array")
        else:
            for i, exp in enumerate(editable['experience']):
                if not isinstance(exp, dict):
                    errors.append(f"experience[{i}] must be an object")
                    continue
                for field in ('title', 'company', 'dates'):
                    if field not in exp:
                        errors.append(f"experience[{i}] missing '{field}'")
                if 'bullets' not in exp:
                    errors.append(f"experience[{i}] missing 'bullets'")
                elif not isinstance(exp['bullets'], list):
                    errors.append(f"experience[{i}].bullets must be an array")
                elif len(exp['bullets']) == 0:
                    errors.append(f"experience[{i}].bullets is empty")

        # Projects
        if 'projects' in editable:
            if not isinstance(editable['projects'], list):
                errors.append("'editable.projects' must be an array")
            else:
                for i, proj in enumerate(editable['projects']):
                    if not isinstance(proj, dict):
                        errors.append(f"projects[{i}] must be an object")
                        continue
                    if 'title' not in proj:
                        errors.append(f"projects[{i}] missing 'title'")
                    if 'description' not in proj:
                        errors.append(f"projects[{i}] missing 'description'")

    return errors


def validate_or_exit(data, source_path):
    """Validate resume schema and exit with error if invalid.

    Args:
        data: Parsed resume JSON dict.
        source_path: Path string for error messages.
    """
    errors = validate_resume_schema(data)
    if errors:
        print(f"ERROR: Schema validation failed for {source_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
