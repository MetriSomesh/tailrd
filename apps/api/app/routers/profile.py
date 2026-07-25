"""Profile and onboarding routes.

All routes require authentication. The onboarding wizard advances step-by-step,
with each step saving its data and advancing the counter.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.profile import (
    EducationIn,
    ExperienceIn,
    OnboardingStepUpdate,
    ParsedResumeResult,
    ProfileBasicsIn,
    ProfileOut,
    ProfileVoiceIn,
    ProjectIn,
    SkillCategoryIn,
)
from app.services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.get_profile(db, user.id)


@router.patch("/basics", response_model=ProfileOut)
async def update_basics(
    body: ProfileBasicsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.update_basics(db, user.id, body)


@router.patch("/voice", response_model=ProfileOut)
async def update_voice(
    body: ProfileVoiceIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.update_voice(db, user.id, body)


@router.post("/step", response_model=ProfileOut)
async def advance_onboarding_step(
    body: OnboardingStepUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.advance_step(db, user.id, body.step)


@router.put("/educations", response_model=ProfileOut)
async def set_educations(
    body: list[EducationIn],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.set_educations(db, user.id, body)


@router.put("/experiences", response_model=ProfileOut)
async def set_experiences(
    body: list[ExperienceIn],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.set_experiences(db, user.id, body)


@router.put("/projects", response_model=ProfileOut)
async def set_projects(
    body: list[ProjectIn],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.set_projects(db, user.id, body)


@router.put("/skills", response_model=ProfileOut)
async def set_skills(
    body: list[SkillCategoryIn],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await profile_service.set_skills(db, user.id, body)


@router.post("/parse-resume", response_model=ParsedResumeResult)
async def parse_resume_upload(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    """Upload a PDF or DOCX resume and extract structured data.

    This is a best-effort extraction. The user reviews and edits the result
    in the onboarding wizard before saving.
    """
    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ("pdf", "docx"):
            raise UnsupportedMediaTypeError("Only PDF and DOCX files are supported.")

    # Read with size guard
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(f"File exceeds {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MB limit.")

    # Extract text
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    raw_text = _extract_text(content, ext)

    # For now, return the raw text. Phase 4+ adds LLM-powered structured extraction.
    # The frontend shows this text and lets the user fill in fields manually.
    return ParsedResumeResult(raw_text=raw_text)


def _extract_text(content: bytes, ext: str) -> str:
    """Extract plain text from a PDF or DOCX file."""
    if ext == "pdf":
        return _extract_pdf_text(content)
    if ext == "docx":
        return _extract_docx_text(content)
    return ""


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception:
        return ""


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        import io

        from docx import Document

        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""
