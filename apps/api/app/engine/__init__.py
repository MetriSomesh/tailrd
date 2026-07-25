"""Resume tailoring engine — ported from the original resume-tailor CLI project.

This package contains the core scoring, generation, and validation logic.
All modules are pure functions operating on dicts/files — no database or
network dependencies. They can be tested independently of FastAPI.

Public API:
- jd_parser: extract skills, responsibilities, qualifications from JD text
- score_ats: score a tailored resume against a JD
- generate_docx: render tailored.json → DOCX bytes
- validate_ats_parsability: check a DOCX is ATS-readable
- validators: schema validation + safe file loaders
"""
