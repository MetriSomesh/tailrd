"""Tailor API: submit jobs, list runs, get status, download DOCX."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_verified_user, require_csrf
from app.core.errors import NotFoundError, OnboardingIncompleteError, QueueUnavailableError
from app.db.base import new_uuid
from app.db.models.profile import Profile
from app.db.models.run import TailorRun
from app.db.models.user import User
from app.db.session import get_session
from app.services.storage import get_storage
from app.workers.runner import enqueue_job

router = APIRouter(tags=["tailor"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TailorRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=15000)
    jd_url: str | None = Field(default=None, max_length=2048)
    company: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)


class RunSummary(BaseModel):
    id: str
    status: str
    jd_label: str | None = None
    company: str | None = None
    role: str | None = None
    overall_score: float | None = None
    created_at: str
    finished_at: str | None = None


class RunDetail(RunSummary):
    jd_text: str | None = None
    tailored_json: dict | None = None
    score_json: dict | None = None
    parsability_json: dict | None = None
    iterations: int = 0
    error_code: str | None = None
    error_message: str | None = None
    docx_storage_key: str | None = None


class TailorResponse(BaseModel):
    run_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tailor", response_model=TailorResponse, status_code=202, dependencies=[Depends(require_csrf)])
async def submit_tailor_job(
    body: TailorRequest,
    user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_session),
):
    """Submit a new tailoring job. Returns 202 with the run_id for polling.

    Requires:
    - Authenticated + verified email
    - Completed onboarding (profile must exist)
    - Quota check (Phase 6)
    """
    # Check onboarding complete
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile or not profile.is_complete:
        raise OnboardingIncompleteError(
            "Complete your profile before tailoring a resume."
        )

    # TODO Phase 6: quota check here

    # Create the run
    run = TailorRun(
        id=new_uuid(),
        user_id=user.id,
        status="queued",
        jd_text=body.jd_text,
        jd_url=body.jd_url,
        jd_label=_extract_label(body.jd_text),
        company=body.company,
        role=body.role,
        entitlement_consumed=True,  # TODO: set properly in Phase 6
    )
    db.add(run)
    await db.commit()

    # Enqueue the job
    enqueued = await enqueue_job(run.id)
    if not enqueued:
        # Redis down — mark the run for retry
        run.status = "queued"
        run.error_message = "Queue temporarily unavailable, will retry."
        await db.commit()
        raise QueueUnavailableError(
            "Job queue is temporarily unavailable. Your request was saved and will be processed shortly.",
            retry_after=10,
        )

    return TailorResponse(
        run_id=run.id,
        status="queued",
        message="Job submitted. Poll GET /runs/{id} for status.",
    )


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all runs for the current user, most recent first."""
    result = await db.execute(
        select(TailorRun)
        .where(TailorRun.user_id == user.id)
        .order_by(TailorRun.created_at.desc())
        .limit(50)
    )
    runs = result.scalars().all()
    return [
        RunSummary(
            id=r.id,
            status=r.status,
            jd_label=r.jd_label,
            company=r.company,
            role=r.role,
            overall_score=r.overall_score,
            created_at=r.created_at.isoformat(),
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get full details of a specific run. Used for polling and result display."""
    result = await db.execute(
        select(TailorRun).where(TailorRun.id == run_id, TailorRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("Run not found.")

    return RunDetail(
        id=run.id,
        status=run.status,
        jd_label=run.jd_label,
        company=run.company,
        role=run.role,
        overall_score=run.overall_score,
        created_at=run.created_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        jd_text=run.jd_text,
        tailored_json=json.loads(run.tailored_json) if run.tailored_json else None,
        score_json=json.loads(run.score_json) if run.score_json else None,
        parsability_json=json.loads(run.parsability_json) if run.parsability_json else None,
        iterations=run.iterations,
        error_code=run.error_code,
        error_message=run.error_message,
        docx_storage_key=run.docx_storage_key,
    )


@router.get("/runs/{run_id}/download")
async def download_run_docx(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Download the generated DOCX for a completed run.

    Returns a redirect to a presigned S3 URL (production) or streams the file
    directly (local dev).
    """
    result = await db.execute(
        select(TailorRun).where(TailorRun.id == run_id, TailorRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("Run not found.")
    if not run.docx_storage_key:
        raise NotFoundError("No DOCX file available for this run.")

    storage = get_storage()

    if settings.STORAGE_BACKEND == "s3":
        url = await storage.get_download_url(run.docx_storage_key)
        return Response(status_code=302, headers={"Location": url})
    # Local: read and stream
    from app.services.storage import LocalStorageBackend

    local = storage
    if not isinstance(local, LocalStorageBackend):
        raise NotFoundError("File not available.")
    data = local.read(run.docx_storage_key)
    if not data:
        raise NotFoundError("File not found in storage.")
    filename = run.docx_storage_key.rsplit("/", 1)[-1]
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_label(jd_text: str) -> str | None:
    """Extract a short label from the first line of the JD."""
    first_line = jd_text.strip().split("\n")[0][:100]
    if first_line:
        return first_line.strip()
    return None
