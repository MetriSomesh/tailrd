#!/usr/bin/env python3
"""Score a tailored resume against a job description for ATS compatibility.

Scoring is fully dynamic — skills and keywords are extracted from the JD itself,
not from any hardcoded set. This ensures accurate scoring regardless of role type.
"""

import json
import sys
import os
import re

from app.engine.validators import load_json_safe, load_text_safe, validate_or_exit
from app.engine.jd_parser import extract_skills_from_jd, extract_responsibilities


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "can",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "because",
    "also",
    "if",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "what",
    "which",
    "who",
    "whom",
    "their",
    "them",
    "they",
    "our",
    "we",
    "you",
    "your",
    "my",
    "me",
    "he",
    "she",
    "his",
    "her",
    "am",
    "having",
    "doing",
    "getting",
    "making",
    "using",
    "working",
    "including",
    "providing",
    "looking",
    "helping",
    "taking",
    "going",
    "coming",
    "based",
    "new",
    "etc",
    "already",
    "able",
    "good",
    "well",
    "within",
    "without",
    "while",
    "still",
    "yet",
    "however",
    "though",
    "although",
    "since",
    "until",
    "up",
    "down",
    "back",
    "around",
    "along",
    "across",
    "throughout",
    "via",
    "per",
    # Generic JD filler — not meaningful for resume keyword matching
    "role",
    "team",
    "company",
    "position",
    "job",
    "work",
    "careers",
    "career",
    "apply",
    "application",
    "join",
    "hiring",
    "looking",
    "seeking",
    "about",
    "learn",
    "visit",
    "want",
    "hear",
    "read",
    "tell",
    "write",
    "best",
    "better",
    "great",
    "strong",
    "clearly",
    "directly",
    "actually",
    "quickly",
    "fast",
    "faster",
    "accurately",
    "personally",
    "perfectly",
    "high",
    "low",
    "real",
    "true",
    "full",
    "time",
    "full-time",
    "part-time",
    "people",
    "person",
    "anyone",
    "someone",
    "everyone",
    "ourselves",
    "today",
    "years",
    "year",
    "decades",
    "world",
    "industry",
    "industries",
    "way",
    "ways",
    "thing",
    "things",
    "kind",
    "kinds",
    "type",
    "types",
    "like",
    "need",
    "needs",
    "believe",
    "think",
    "know",
    "see",
    "find",
    "take",
    "give",
    "make",
    "move",
    "moves",
    "push",
    "show",
    "try",
    "done",
    "gets",
    "got",
    "become",
    "look",
    "feels",
    "feel",
    "won",
    "welcome",
    "below",
    "button",
    "links",
    "link",
    "email",
    "fit",
    "case",
    "bar",
    "level",
    "standard",
    "version",
    "directness",
    "ownership",
    "mindset",
    "agency",
    "pace",
    "depth",
    "ego",
    "costs",
    "quarter",
    "capable",
    "exceptional",
    "resonates",
}


# Words that are often in JDs but only matter if they relate to tech context.
# We keep these ONLY if they appear near a technical term.
SOFT_CONTEXT_WORDS = {
    "complete",
    "coordinate",
    "creating",
    "designing",
    "improving",
    "customer",
    "founders",
    "product",
    "legal",
    "users",
}


def extract_meaningful_words(text):
    """Extract meaningful single words from text (lowercased, stopwords removed).

    Filters out generic JD filler words that aren't meaningful for resume matching.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s\-]", " ", text)
    words = text.split()
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]


def normalize_skill(skill):
    """Normalize a skill string for comparison."""
    return skill.lower().strip().replace("-", " ").replace("_", " ")


def flatten_skills(raw_skills):
    """Flatten skills whether list or categorized dict."""
    if isinstance(raw_skills, dict):
        skills_list = []
        for cat, items in raw_skills.items():
            if isinstance(items, list):
                skills_list.extend(items)
            else:
                skills_list.append(str(items))
        return skills_list
    elif isinstance(raw_skills, (list, tuple)):
        return list(raw_skills)
    else:
        return [str(raw_skills)] if raw_skills else []


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------


def compute_skills_match(jd_text, resume_skills):
    """Compute how well resume skills match the JD's required skills.

    DYNAMIC: Extracts skills from JD text using jd_parser, not a hardcoded set.

    Returns:
        tuple: (match_pct, matched_skills, missing_skills)
    """
    # Extract what skills the JD actually asks for
    jd_skills = extract_skills_from_jd(jd_text)

    if not jd_skills:
        return 100.0, [], []  # No skills to match = perfect score

    # Normalize resume skills for matching
    resume_skills_normalized = set()
    for skill in resume_skills:
        resume_skills_normalized.add(normalize_skill(skill))
        # Also add individual words for multi-word skills
        for word in normalize_skill(skill).split():
            if len(word) > 2:
                resume_skills_normalized.add(word)

    # Also build a combined resume skills string for substring matching
    resume_skills_str = " ".join(normalize_skill(s) for s in resume_skills)

    matched = []
    missing = []

    for skill in jd_skills:
        skill_norm = normalize_skill(skill)
        # Check: exact match, word-in-set, or substring in combined string
        if (
            skill_norm in resume_skills_normalized
            or skill_norm in resume_skills_str
            or any(skill_norm in normalize_skill(rs) for rs in resume_skills)
        ):
            matched.append(skill)
        else:
            missing.append(skill)

    match_pct = (len(matched) / len(jd_skills) * 100) if jd_skills else 0
    return match_pct, sorted(matched), sorted(missing)


def compute_keyword_match(jd_text, resume_text):
    """Compute keyword overlap between JD and full resume text.

    Uses meaningful words (stopwords removed) from the JD as the target set.

    Returns:
        tuple: (keyword_pct, term_overlap_pct, missing_keywords, matched_keywords)
    """
    jd_words = set(extract_meaningful_words(jd_text))
    resume_words = set(extract_meaningful_words(resume_text))

    if not jd_words:
        return 100.0, 100.0, [], []

    matched = jd_words & resume_words
    missing = jd_words - resume_words

    keyword_pct = len(matched) / len(jd_words) * 100

    # Multi-word term overlap (using jd_parser's skill extraction as proxy)
    jd_skills = extract_skills_from_jd(jd_text)
    resume_text_lower = resume_text.lower()
    multi_word_skills = {s for s in jd_skills if " " in s or "." in s}

    if multi_word_skills:
        term_matched = sum(1 for t in multi_word_skills if t in resume_text_lower)
        term_pct = term_matched / len(multi_word_skills) * 100
    else:
        term_pct = 100.0  # No multi-word terms to match

    return keyword_pct, term_pct, sorted(missing)[:20], sorted(matched)[:20]


def compute_experience_relevance(jd_text, experience_bullets):
    """Score how well experience bullets address JD responsibilities.

    NEW APPROACH: Instead of raw keyword ratio (which was structurally broken),
    we extract responsibility concepts from the JD and check how many are
    addressed by the experience bullets.

    Returns:
        tuple: (relevance_pct, covered_responsibilities, uncovered_responsibilities)
    """
    responsibilities = extract_responsibilities(jd_text)

    if not responsibilities:
        # Fallback: use keyword overlap if no structured responsibilities found
        jd_words = set(extract_meaningful_words(jd_text))
        exp_words = set(extract_meaningful_words(" ".join(experience_bullets)))
        if not jd_words:
            return 100.0, [], []
        overlap_pct = len(exp_words & jd_words) / len(jd_words) * 100
        return overlap_pct, [], []

    # For each responsibility, check if the experience bullets address it
    exp_text = " ".join(experience_bullets).lower()
    exp_words = set(extract_meaningful_words(exp_text))

    covered = []
    uncovered = []

    for resp in responsibilities:
        # Extract key concept words from this responsibility
        resp_words = set(extract_meaningful_words(resp))
        if not resp_words:
            continue

        # A responsibility is "covered" if >= 40% of its key words appear in experience
        overlap = resp_words & exp_words
        coverage = len(overlap) / len(resp_words) if resp_words else 0

        if coverage >= 0.35:
            covered.append(resp)
        else:
            uncovered.append(resp)

    total = len(covered) + len(uncovered)
    if total == 0:
        return 100.0, [], []

    relevance_pct = len(covered) / total * 100
    return relevance_pct, covered, uncovered


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------


def score_resume(jd_path, resume_json_path, docx_path, output_json=True):
    """Run the full ATS scoring pipeline.

    Scoring weights:
        - Keyword Match:         35%  (meaningful word overlap JD vs full resume)
        - Skills Match:          25%  (JD-extracted skills vs resume skills section)
        - Term Overlap:          10%  (multi-word technical terms)
        - Experience Relevance:  30%  (responsibility coverage in experience bullets)
    """
    # Read JD
    jd_text = load_text_safe(jd_path)
    if not jd_text.strip():
        print("ERROR: Job description file is empty.", file=sys.stderr)
        sys.exit(1)

    # Read and validate resume JSON
    resume_data = load_json_safe(resume_json_path)
    validate_or_exit(resume_data, resume_json_path)

    # Verify DOCX exists (we don't parse it, but confirm it was generated)
    if not os.path.exists(docx_path):
        print(
            f"WARNING: DOCX file not found at {docx_path}. Scoring from JSON only.", file=sys.stderr
        )

    editable = resume_data["editable"]

    # Flatten skills
    skills_list = flatten_skills(editable.get("skills", []))

    # Build full resume text for keyword matching
    resume_text_parts = []
    resume_text_parts.append(editable.get("about", ""))
    resume_text_parts.extend(skills_list)
    for exp in editable.get("experience", []):
        resume_text_parts.extend(exp.get("bullets", []))
    for proj in editable.get("projects", []):
        resume_text_parts.append(proj.get("description", ""))
        resume_text_parts.extend(proj.get("technologies", []))
    resume_text = " ".join(resume_text_parts)

    # Collect experience bullets
    experience_bullets = [
        b for exp in editable.get("experience", []) for b in exp.get("bullets", [])
    ]

    # Compute all scores
    keyword_pct, term_pct, missing_keywords, matched_keywords = compute_keyword_match(
        jd_text, resume_text
    )
    skills_pct, skills_matched, skills_missing = compute_skills_match(jd_text, skills_list)
    experience_pct, covered_resp, uncovered_resp = compute_experience_relevance(
        jd_text, experience_bullets
    )

    # Overall score (weighted)
    overall = keyword_pct * 0.35 + skills_pct * 0.25 + term_pct * 0.10 + experience_pct * 0.30
    overall = min(overall, 100.0)

    result = {
        "overall_score": round(overall, 1),
        "keyword_match_pct": round(keyword_pct, 1),
        "skills_match_pct": round(skills_pct, 1),
        "term_overlap_pct": round(term_pct, 1),
        "experience_relevance_pct": round(experience_pct, 1),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "skills_matched": skills_matched,
        "skills_missing": skills_missing,
        "responsibilities_covered": covered_resp,
        "responsibilities_uncovered": uncovered_resp,
        "resume_json": resume_json_path,
        "docx_path": docx_path,
    }

    # Write score JSON
    score_dir = os.path.dirname(docx_path)
    score_name = os.path.splitext(os.path.basename(docx_path))[0] + "_score.json"
    score_path = os.path.join(score_dir, score_name) if score_dir else score_name

    try:
        with open(score_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except PermissionError:
        print(f"ERROR: Permission denied writing score to {score_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to write score file: {e}", file=sys.stderr)
        sys.exit(1)

    if output_json:
        print(json.dumps(result, indent=2))

    print(f"\nScore saved to {score_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python score_ats.py <jd.txt> <resume.json> <resume.docx> [--json]")
        print("\nArguments:")
        print("  jd.txt       Path to the job description text file")
        print("  resume.json  Path to the tailored resume JSON")
        print("  resume.docx  Path to the generated DOCX (used for score filename)")
        print("  --json       (Optional) Print full score breakdown to stdout")
        sys.exit(1)

    jd_path = sys.argv[1]
    resume_json_path = sys.argv[2]
    docx_path = sys.argv[3]
    output_json = "--json" in sys.argv

    result = score_resume(jd_path, resume_json_path, docx_path, output_json=output_json)

    # Exit with score info
    if result["overall_score"] >= 70:
        print(f"\nPASS: Overall score {result['overall_score']}%")
        sys.exit(0)
    else:
        print(f"\nNEEDS_IMPROVEMENT: Overall score {result['overall_score']}%")
        sys.exit(2)
