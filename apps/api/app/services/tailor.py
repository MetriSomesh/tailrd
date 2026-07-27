"""Tailor service: orchestrates the full resume tailoring pipeline.

Called by the worker when a job is dequeued. Steps:
1. Update run status to running
2. Build base_resume.json from profile
3. Run the agent (mock or opencode)
4. Generate DOCX from tailored JSON
5. Score the result
6. Upload DOCX to storage
7. Update run with results
"""

from __future__ import annotations

import json
import os
import tempfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    REFUNDABLE_ERROR_CODES,
    AgentOutputInvalidError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.models.run import TailorRun
from app.services.agent import run_agent
from app.services.storage import generate_storage_key, get_storage

log = get_logger(__name__)


async def _set_progress(
    db: AsyncSession, run: TailorRun, progress: int, stage: str
) -> None:
    """Persist a progress checkpoint so the polling frontend can render a live bar.

    Committed immediately (not batched) because the whole point is that a
    concurrently-polling request sees the update mid-pipeline.
    """
    run.progress = progress
    run.progress_stage = stage
    await db.commit()


def _build_feedback(score_result: dict, target: float) -> str:
    """Turn a score breakdown into a concise, truthful revision brief for the agent.

    Names the concrete gaps (missing skills/keywords, uncovered responsibilities)
    while explicitly forbidding fabrication, so the next draft closes real gaps
    rather than padding with things the candidate can't defend.
    """
    overall = score_result.get("overall_score", 0.0)
    lines = [
        f"The last draft scored {overall}/100 (target {target:g}). Push the match "
        "higher by covering the gaps below. You may edit everything except the "
        "candidate's name, contact, education, and each role's employer (company)."
    ]

    skills_missing = score_result.get("skills_missing") or []
    if skills_missing:
        lines.append(
            "- Skills the job asks for that are missing — add them to the skills "
            "section and reflect them in experience/projects so the resume covers "
            f"the target stack: {', '.join(skills_missing[:12])}."
        )

    missing_keywords = score_result.get("missing_keywords") or []
    if missing_keywords:
        lines.append(
            "- Relevant terms to weave into the summary, skills and bullets: "
            f"{', '.join(missing_keywords[:15])}."
        )

    uncovered = score_result.get("responsibilities_uncovered") or []
    if uncovered:
        joined = "; ".join(u[:120] for u in uncovered[:6])
        lines.append(
            "- Job responsibilities not yet reflected — rewrite experience bullets "
            f"and project descriptions to demonstrate these: {joined}."
        )

    return "\n".join(lines)


async def execute_tailor_job(db: AsyncSession, run_id: str) -> None:
    """Execute the full tailoring pipeline for a given run.

    This is the function the worker calls. It manages the full lifecycle:
    status transitions, error handling, entitlement refunds.
    """
    # Load the run
    result = await db.execute(select(TailorRun).where(TailorRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        log.error("tailor_job_run_not_found", run_id=run_id)
        return

    if run.status != "queued":
        log.warning("tailor_job_skip_not_queued", run_id=run_id, status=run.status)
        return

    # Mark as running
    run.status = "running"
    run.started_at = utcnow()
    run.progress = 5
    run.progress_stage = "scraping"
    await db.commit()

    try:
        # 0. Resolve the JD text. The primary input is a posting URL, which we
        #    scrape here (headless browser) into plain text.
        jd_text = (run.jd_text or "").strip()
        if run.jd_url and len(jd_text) < 120:
            await _set_progress(db, run, 10, "scraping")
            from app.services.jd_scraper import scrape_jd

            jd_text = await scrape_jd(run.jd_url)
            run.jd_text = jd_text
            if not run.jd_label:
                first_line = jd_text.split("\n", 1)[0][:100].strip()
                run.jd_label = first_line or None
            await db.commit()
            log.info("tailor_job_jd_scraped", run_id=run_id, chars=len(jd_text))

        # 1. Build base resume from user profile
        await _set_progress(db, run, 25, "building")
        from app.services.profile import build_base_resume_json

        base_resume = await build_base_resume_json(db, run.user_id)

        # 2. Get allow_ai_projects setting
        from app.db.models.profile import Profile

        profile_result = await db.execute(select(Profile).where(Profile.user_id == run.user_id))
        profile = profile_result.scalar_one_or_none()
        allow_ai_projects = profile.allow_ai_projects if profile else False

        # 3. Tailor iteratively: rewrite → score → if below target, feed the gaps
        #    back to the agent and try again, keeping the best-scoring draft.
        #    Bounded by MAX_ITERATIONS so latency/cost stay predictable.
        target = settings.TARGET_SCORE
        max_iterations = max(1, settings.MAX_ITERATIONS)

        best_tailored: dict | None = None
        best_score_result: dict | None = None
        best_overall = -1.0
        feedback: str | None = None
        attempts = 0

        for attempt in range(1, max_iterations + 1):
            # Progress climbs across attempts but stays inside the tailoring band.
            await _set_progress(db, run, min(45 + (attempt - 1) * 12, 74), "tailoring")

            try:
                agent_result = await run_agent(
                    base_resume=base_resume,
                    jd_text=jd_text,
                    allow_ai_projects=allow_ai_projects,
                    feedback=feedback,
                )
            except (
                AgentTimeoutError,
                AgentUnavailableError,
                AgentOutputInvalidError,
            ) as exc:
                # A revision attempt can fail (e.g. the free model occasionally
                # emits no file). If we already have a good draft, keep it rather
                # than discarding all the work. Only propagate when there's
                # nothing to fall back on (the very first attempt).
                if best_tailored is not None:
                    log.warning(
                        "tailor_job_revision_failed_keeping_best",
                        run_id=run_id,
                        attempt=attempt,
                        best=best_overall,
                        error=str(exc)[:200],
                    )
                    break
                raise

            attempts = attempt

            candidate = agent_result.tailored_json
            candidate_score = _score_tailored(candidate, jd_text)
            candidate_overall = candidate_score.get("overall_score", 0.0)

            improved = candidate_overall > best_overall
            if improved:
                best_tailored = candidate
                best_score_result = candidate_score
                best_overall = candidate_overall

            log.info(
                "tailor_job_iteration",
                run_id=run_id,
                attempt=attempt,
                score=candidate_overall,
                best=best_overall,
                target=target,
            )

            # Stop when good enough, out of tries, or a revision stopped helping.
            if candidate_overall >= target or attempt == max_iterations:
                break
            if attempt > 1 and not improved:
                break

            feedback = _build_feedback(candidate_score, target)

        tailored = best_tailored
        score_result = best_score_result
        run.iterations = attempts

        # 4. Generate DOCX for the best-scoring draft
        await _set_progress(db, run, 80, "generating")
        docx_bytes = _generate_docx_bytes(tailored)

        # 5. Scoring already done in the loop — checkpoint for the UI.
        await _set_progress(db, run, 88, "scoring")

        # 6. Upload DOCX to storage
        await _set_progress(db, run, 94, "uploading")
        storage = get_storage()
        filename = f"Resume_{run.id[:8]}.docx"
        storage_key = generate_storage_key(run.user_id, run.id, filename)
        await storage.upload(
            docx_bytes,
            storage_key,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # 7. Update run with success
        run.status = "succeeded"
        run.tailored_json = json.dumps(tailored)
        run.score_json = json.dumps(score_result)
        run.overall_score = score_result.get("overall_score", 0)
        run.docx_storage_key = storage_key
        run.progress = 100
        run.progress_stage = "done"
        run.finished_at = utcnow()

        await db.commit()
        log.info(
            "tailor_job_succeeded",
            run_id=run_id,
            score=run.overall_score,
            iterations=run.iterations,
        )

    except Exception as exc:
        # Determine error code
        error_code = getattr(exc, "code", "internal_error")
        error_message = str(exc)[:500]

        run.status = "failed"
        run.error_code = error_code
        run.error_message = error_message
        run.progress_stage = "failed"
        run.finished_at = utcnow()

        # Auto-refund entitlement on system errors (not on user-caused ones).
        if (
            error_code in REFUNDABLE_ERROR_CODES
            and run.entitlement_consumed
            and not run.entitlement_refunded
        ):
            from app.services.quota import refund_entitlement

            await refund_entitlement(db, run.user_id, run.entitlement_source or "free")
            run.entitlement_refunded = True
            log.info(
                "tailor_job_entitlement_refunded",
                run_id=run_id,
                error_code=error_code,
                source=run.entitlement_source,
            )

        await db.commit()
        log.error(
            "tailor_job_failed",
            run_id=run_id,
            error_code=error_code,
            error=error_message[:200],
        )


def _generate_docx_bytes(tailored: dict) -> bytes:
    """Generate DOCX from tailored JSON, returning raw bytes.

    Uses a temp file because python-docx's Document.save() needs a path or stream.
    """
    from app.engine.generate_docx import generate_resume

    # Write tailored JSON to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(tailored, f)
        json_path = f.name

    # Generate DOCX to a temp file
    docx_path = json_path.replace(".json", ".docx")

    try:
        generate_resume(json_path, docx_path)
        with open(docx_path, "rb") as f:
            return f.read()
    finally:
        # Clean up temp files
        import contextlib

        for p in (json_path, docx_path):
            with contextlib.suppress(OSError):
                os.unlink(p)


def _score_tailored(tailored: dict, jd_text: str) -> dict:
    """Score the tailored resume against the JD.

    Runs the scoring engine in-process (pure Python, no subprocess needed).
    """
    from app.engine.score_ats import (
        compute_experience_relevance,
        compute_keyword_match,
        compute_skills_match,
        flatten_skills,
    )

    editable = tailored.get("editable", {})
    skills_list = flatten_skills(editable.get("skills", []))

    # Build full resume text
    resume_text_parts = [editable.get("about", "")]
    resume_text_parts.extend(skills_list)
    for exp in editable.get("experience", []):
        resume_text_parts.extend(exp.get("bullets", []))
    for proj in editable.get("projects", []):
        resume_text_parts.append(proj.get("description", ""))
        resume_text_parts.extend(proj.get("technologies", []))
    resume_text = " ".join(resume_text_parts)

    # Compute scores
    keyword_pct, term_pct, missing_keywords, matched_keywords = compute_keyword_match(
        jd_text, resume_text
    )
    skills_pct, skills_matched, skills_missing = compute_skills_match(jd_text, skills_list)

    experience_bullets = [
        b for exp in editable.get("experience", []) for b in exp.get("bullets", [])
    ]
    experience_pct, covered_resp, uncovered_resp = compute_experience_relevance(
        jd_text, experience_bullets
    )

    overall = min(
        keyword_pct * 0.35 + skills_pct * 0.25 + term_pct * 0.10 + experience_pct * 0.30,
        100.0,
    )

    return {
        "overall_score": round(overall, 1),
        "keyword_match_pct": round(keyword_pct, 1),
        "skills_match_pct": round(skills_pct, 1),
        "term_overlap_pct": round(term_pct, 1),
        "experience_relevance_pct": round(experience_pct, 1),
        "matched_keywords": matched_keywords[:20],
        "missing_keywords": missing_keywords[:20],
        "skills_matched": skills_matched,
        "skills_missing": skills_missing,
        "responsibilities_covered": covered_resp[:10],
        "responsibilities_uncovered": uncovered_resp[:10],
    }
