#!/usr/bin/env python3
"""Parse job descriptions to extract skills, requirements, and responsibilities dynamically.

This replaces the old hardcoded skills set with JD-aware extraction.
"""

import re


# Comprehensive tech dictionary — terms we recognize as "skills" when found in a JD.
# This is the lookup table, NOT the scoring target. Only terms actually in the JD get scored.
TECH_DICTIONARY = {
    # Languages
    "python",
    "javascript",
    "typescript",
    "java",
    "c#",
    "c++",
    "c",
    "go",
    "golang",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "r",
    "perl",
    "lua",
    "dart",
    "elixir",
    "haskell",
    "clojure",
    "sql",
    "html",
    "css",
    "sass",
    "less",
    "bash",
    "shell",
    "powershell",
    # Frontend frameworks
    "react",
    "reactjs",
    "react.js",
    "angular",
    "angularjs",
    "vue",
    "vuejs",
    "vue.js",
    "svelte",
    "next.js",
    "nextjs",
    "nuxt",
    "nuxtjs",
    "gatsby",
    "remix",
    "tailwindcss",
    "tailwind",
    "bootstrap",
    "material-ui",
    "mui",
    "chakra",
    # Backend frameworks
    "node.js",
    "nodejs",
    "express",
    "expressjs",
    "fastapi",
    "flask",
    "django",
    "spring",
    "spring boot",
    "asp.net",
    ".net",
    "rails",
    "ruby on rails",
    "laravel",
    "gin",
    "fiber",
    "actix",
    "nest.js",
    "nestjs",
    "koa",
    # Mobile
    "react native",
    "flutter",
    "swift",
    "swiftui",
    "kotlin",
    "android",
    "ios",
    "xamarin",
    "ionic",
    "expo",
    # AI/ML
    "machine learning",
    "deep learning",
    "nlp",
    "natural language processing",
    "computer vision",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "sklearn",
    "langchain",
    "llm",
    "llms",
    "large language model",
    "large language models",
    "gpt",
    "openai",
    "anthropic",
    "hugging face",
    "huggingface",
    "transformers",
    "rag",
    "retrieval augmented generation",
    "vector database",
    "embeddings",
    "fine-tuning",
    "prompt engineering",
    "agents",
    "agentic",
    "multi-agent",
    "guardrails",
    "evals",
    "benchmarks",
    # Databases
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "dynamodb",
    "cassandra",
    "sqlite",
    "neo4j",
    "pinecone",
    "weaviate",
    "chromadb",
    "pgvector",
    "supabase",
    "firebase",
    "firestore",
    "prisma",
    "sequelize",
    "sqlalchemy",
    "typeorm",
    # Cloud & Infrastructure
    "aws",
    "amazon web services",
    "gcp",
    "google cloud",
    "azure",
    "heroku",
    "vercel",
    "netlify",
    "digital ocean",
    "cloudflare",
    "ec2",
    "ecs",
    "lambda",
    "s3",
    "rds",
    "sqs",
    "sns",
    "cloudformation",
    "terraform",
    "pulumi",
    "cdk",
    # DevOps & Tools
    "docker",
    "kubernetes",
    "k8s",
    "helm",
    "jenkins",
    "github actions",
    "gitlab ci",
    "circleci",
    "ci/cd",
    "ci cd",
    "ansible",
    "nginx",
    "apache",
    # Version control
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "svn",
    # Data & Messaging
    "kafka",
    "rabbitmq",
    "celery",
    "airflow",
    "spark",
    "hadoop",
    "flink",
    "pandas",
    "numpy",
    "dbt",
    "snowflake",
    "bigquery",
    "redshift",
    "etl",
    # API & Protocols
    "rest",
    "rest api",
    "rest apis",
    "restful",
    "graphql",
    "grpc",
    "websocket",
    "websockets",
    "soap",
    "openapi",
    "swagger",
    # Testing
    "jest",
    "pytest",
    "unittest",
    "mocha",
    "cypress",
    "selenium",
    "playwright",
    "testing",
    "unit testing",
    "integration testing",
    "e2e",
    "tdd",
    "bdd",
    # Concepts & Methodologies
    "microservices",
    "monolith",
    "event-driven",
    "serverless",
    "distributed systems",
    "system design",
    "design patterns",
    "solid",
    "clean architecture",
    "domain-driven design",
    "ddd",
    "cqrs",
    "event sourcing",
    "agile",
    "scrum",
    "kanban",
    "sdlc",
    "devops",
    "sre",
    "oop",
    "oops",
    "object-oriented",
    "object oriented",
    "functional programming",
    "data structures",
    "algorithms",
    "problem solving",
    "problem-solving",
    "concurrency",
    "multithreading",
    "async",
    "asynchronous",
    # Observability & Monitoring
    "observability",
    "monitoring",
    "logging",
    "metrics",
    "tracing",
    "datadog",
    "grafana",
    "prometheus",
    "splunk",
    "new relic",
    "sentry",
    "elk",
    "elasticsearch",
    "logstash",
    "kibana",
    # Security
    "oauth",
    "jwt",
    "authentication",
    "authorization",
    "rbac",
    "encryption",
    "ssl",
    "tls",
    "https",
    "security",
    "penetration testing",
    "owasp",
}

# Multi-word terms that need phrase matching (not single-word)
MULTI_WORD_TERMS = {t for t in TECH_DICTIONARY if " " in t or "." in t or "-" in t}
SINGLE_WORD_TERMS = TECH_DICTIONARY - MULTI_WORD_TERMS


def extract_skills_from_jd(jd_text):
    """Extract technical skills/tools/concepts actually mentioned in the JD.

    Returns:
        set: Skills found in the JD (lowercased).
    """
    jd_lower = jd_text.lower()
    found_skills = set()

    # Check multi-word terms first (phrase matching)
    for term in MULTI_WORD_TERMS:
        # Use word boundary-ish matching
        pattern = r"(?:^|[\s,;:(])" + re.escape(term) + r"(?:[\s,;:).]|$)"
        if re.search(pattern, jd_lower):
            found_skills.add(term)

    # Check single-word terms
    # Strip trailing dots/punctuation from words for clean matching
    jd_words = set()
    for word in re.findall(r"[a-z0-9#+.\-]+", jd_lower):
        # Strip trailing periods that aren't part of tech terms (e.g. "Node.js" vs "Python.")
        cleaned = word.rstrip(".")
        if cleaned:
            jd_words.add(cleaned)
        jd_words.add(word)  # Also keep original for terms like "next.js"

    for term in SINGLE_WORD_TERMS:
        if term in jd_words:
            found_skills.add(term)

    return found_skills


def extract_sections(jd_text):
    """Parse JD into logical sections.

    Returns:
        dict: Section name -> list of lines.
    """
    sections = {}
    current_section = "general"
    sections[current_section] = []

    section_headers = [
        "responsibilities",
        "qualifications",
        "requirements",
        "skills",
        "about us",
        "about the team",
        "about the role",
        "the role",
        "what you will do",
        "what you'll own",
        "what we are looking for",
        "what we're looking for",
        "what you bring",
        "nice to have",
        "preferred",
        "bonus",
        "job info",
        "benefits",
        "who you are",
        "your impact",
        "key responsibilities",
        "who thrives here",
        "how to apply",
        "culture",
        "values",
        # Marketing / company-narrative headers. Recognised so they segment into
        # their own sections and can be excluded from scoring signal.
        "what we do",
        "who we are",
        "our mission",
        "the mission",
        "our story",
        "why ",
        "perks",
        "the perks",
        "what makes you",
        "what we don't want",
        "don't want",
        "best suited for",
        "life at",
        "equal opportunity",
        "diversity",
    ]

    for line in jd_text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        line_lower = line_stripped.lower().rstrip(":").strip()

        # Check if this line is a section header
        is_header = False
        for header in section_headers:
            if header in line_lower and len(line_stripped) < 80:
                current_section = line_stripped.rstrip(":").strip()
                sections[current_section] = []
                is_header = True
                break

        if not is_header:
            sections[current_section].append(line_stripped)

    return sections


def extract_responsibilities(jd_text):
    """Extract responsibility statements from the JD.

    Filters out culture/values statements that aren't actionable responsibilities
    (e.g., "Speed with depth", "Raise the bar", "Directness").

    Returns:
        list: Responsibility strings (bullet points or sentences).
    """
    sections = extract_sections(jd_text)
    responsibilities = []

    # Sections to SKIP — these contain culture/values, not responsibilities
    skip_patterns = [
        "thrives",
        "culture",
        "values",
        "benefits",
        "perks",
        "how to apply",
        "about us",
        "about the company",
        "don't see",
        "open application",
        "what to include",
    ]

    # Look for responsibility-related sections
    responsibility_keys = []
    for key in sections:
        key_lower = key.lower()
        # Skip culture/values sections
        if any(skip in key_lower for skip in skip_patterns):
            continue
        if any(
            kw in key_lower
            for kw in [
                "responsibilit",
                "what you will do",
                "what you'll own",
                "your impact",
                "key responsibilit",
                "the role",
                "what we're looking",
                "looking for",
                "qualif",
                "requirement",
            ]
        ):
            responsibility_keys.append(key)

    # If no explicit section found, fall back to general section
    if not responsibility_keys:
        responsibility_keys = ["general"]

    for key in responsibility_keys:
        for line in sections.get(key, []):
            # Strip bullet markers
            cleaned = re.sub(r"^[\s\-•*·▪]+", "", line).strip()
            if cleaned and len(cleaned) > 15:  # Skip very short lines
                # Filter out culture/soft-value and marketing-narrative statements
                if _is_noise_line(cleaned):
                    continue
                responsibilities.append(cleaned)

    return responsibilities


def _is_culture_statement(text):
    """Detect if a line is a culture/values statement rather than a real responsibility.

    Culture statements are typically:
    - Short aphorisms ("Raise the bar")
    - Personality traits ("High ownership", "Directness")
    - Meta-statements about work style without technical content

    Returns:
        bool: True if this is a culture statement to skip.
    """
    text_lower = text.lower()

    # Pattern 1: "Label: explanation" format common in culture sections
    # e.g., "High ownership: You own outcomes, not tasks."
    # e.g., "Speed with depth: You move fast without lowering the standard."
    culture_labels = [
        "high ownership",
        "speed with depth",
        "directness",
        "comfort with ambiguity",
        "raise the bar",
        "high-agency",
        "high agency",
        "ego",
        "no ego",
        "move fast",
        "bias for action",
        "default to action",
        "low ego",
        "radical candor",
        "radical transparency",
        "first principles",
        "growth mindset",
        "intellectual curiosity",
        "humble",
        "hungry",
        "smart",
        "grit",
        "resilience",
        "passion",
        "passionate",
    ]
    for label in culture_labels:
        if text_lower.startswith(label) or f": {label}" in text_lower:
            return True

    # Pattern 2: No technical content + very short
    # If it's under 60 chars and has no tech words, it's likely a culture statement
    from app.engine.jd_parser import TECH_DICTIONARY

    if len(text) < 80:
        text_words = set(text_lower.split())
        has_tech = any(term in text_lower for term in TECH_DICTIONARY if len(term) > 3)
        if not has_tech:
            # Check for culture keywords
            culture_signals = {
                "ownership",
                "mindset",
                "agency",
                "bar",
                "ego",
                "pace",
                "depth",
                "directness",
                "candor",
                "grit",
                "humble",
                "hungry",
                "passion",
                "curiosity",
                "resilience",
                "empathy",
                "transparency",
            }
            if text_words & culture_signals:
                return True

    return False


# Section names that carry company marketing / culture / benefits rather than the
# actual job requirements. Excluded from the scoring signal so a verbose career
# page ("What We Do", "Why <company>?", "The Perks") doesn't dilute the match.
NOISE_SECTION_KEYWORDS = (
    "about us",
    "about the company",
    "about the team",
    "who we are",
    "what we do",
    "our mission",
    "the mission",
    "our story",
    "why ",
    "perks",
    "benefit",
    "culture",
    "values",
    "what makes you",
    "what we don't",
    "don't want",
    "thrives",
    "how to apply",
    "life at",
    "equal opportunity",
    "diversity",
    "eeo",
)

# Opening phrases that mark first/second-person recruiting narrative rather than a
# concrete duty or requirement.
_NARRATIVE_PREFIXES = (
    "we're",
    "we are",
    "we want",
    "we don't",
    "we do not",
    "we need",
    "we believe",
    "we look",
    "we seek",
    "we value",
    "if you",
    "you won't",
    "you will not",
    "sound like you",
    "does this sound",
    "join us",
    "come build",
    "ready to",
)


def is_noise_section(name: str) -> bool:
    """True if a section name is company marketing/culture rather than requirements."""
    n = name.lower().strip()
    return any(k in n for k in NOISE_SECTION_KEYWORDS)


def _has_tech(text: str) -> bool:
    """True if the line names any recognised technical skill/tool/concept."""
    return bool(extract_skills_from_jd(text))


def _is_noise_line(text: str) -> bool:
    """True if a line is culture/marketing narrative rather than a real duty.

    Kept deliberately conservative: a line that names any concrete technology is
    always retained, so genuine responsibilities are never dropped.
    """
    if _is_culture_statement(text):
        return True
    # Normalise smart quotes so prefix checks match scraped text ("We're" often
    # arrives with a curly apostrophe that wouldn't match a straight one).
    tl = text.lower().strip().replace("\u2019", "'").replace("\u2018", "'")
    if not tl:
        return True
    if _has_tech(text):
        return False
    # Rhetorical marketing questions ("Sound like you?", "Why join us?").
    if tl.endswith("?") and len(text) < 90:
        return True
    # First/second-person recruiting narrative with no technical substance.
    if any(tl.startswith(p) for p in _NARRATIVE_PREFIXES):
        return True
    # Motivational filler.
    if any(w in tl for w in ("crave", "obsessed", "allergic", "we offer", "you'll love")):
        return True
    return False


def extract_signal_sections_text(jd_text):
    """Return only the requirement-bearing text of a JD.

    Drops the catch-all "general" preamble and any marketing/culture sections,
    and strips marketing-narrative lines from what remains. Used to build the
    keyword-scoring target so company boilerplate doesn't dilute the match.
    """
    sections = extract_sections(jd_text)
    parts = []
    for name, lines in sections.items():
        if name == "general" or is_noise_section(name):
            continue
        for line in lines:
            if _is_noise_line(line):
                continue
            parts.append(line)
    return "\n".join(parts).strip()


def extract_required_qualifications(jd_text):
    """Extract required qualifications/skills section content.

    Returns:
        list: Qualification strings.
    """
    sections = extract_sections(jd_text)
    qualifications = []

    qual_keys = []
    for key in sections:
        key_lower = key.lower()
        if any(
            kw in key_lower
            for kw in [
                "qualif",
                "requirement",
                "skills",
                "what we are looking",
                "what you bring",
                "who you are",
            ]
        ):
            qual_keys.append(key)

    for key in qual_keys:
        for line in sections.get(key, []):
            cleaned = re.sub(r"^[\s\-•*·▪]+", "", line).strip()
            if cleaned and len(cleaned) > 10:
                if _is_noise_line(cleaned):
                    continue
                qualifications.append(cleaned)

    return qualifications


def analyze_jd(jd_text):
    """Full JD analysis — returns structured extraction.

    Returns:
        dict: {
            'skills': set of skills found,
            'responsibilities': list of responsibility statements,
            'qualifications': list of qualification statements,
            'sections': dict of all parsed sections,
        }
    """
    return {
        "skills": extract_skills_from_jd(jd_text),
        "responsibilities": extract_responsibilities(jd_text),
        "qualifications": extract_required_qualifications(jd_text),
        "sections": extract_sections(jd_text),
    }


if __name__ == "__main__":
    """CLI mode: analyze a JD file and print results."""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python jd_parser.py <jd.txt>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        jd_text = f.read()

    result = analyze_jd(jd_text)
    # Convert set to sorted list for JSON output
    result["skills"] = sorted(result["skills"])

    print(json.dumps(result, indent=2))
