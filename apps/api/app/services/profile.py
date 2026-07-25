"""Profile service: CRUD for profile data, onboarding progression."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import new_uuid, utcnow
from app.db.models.profile import Education, Experience, Profile, Project, SkillCategory
from app.schemas.profile import (
    EducationIn,
    EducationOut,
    ExperienceIn,
    ExperienceOut,
    ProfileBasicsIn,
    ProfileOut,
    ProfileVoiceIn,
    ProjectIn,
    ProjectOut,
    SkillCategoryIn,
    SkillCategoryOut,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_or_create_profile(db: AsyncSession, user_id: str) -> Profile:
    """Get the user's profile, creating it if it doesn't exist (lazy init).

    Always returns a profile with relationships loaded (selectin).
    """
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(id=new_uuid(), user_id=user_id)
        db.add(profile)
        await db.flush()
        # Refresh to properly initialize selectin relationships
        await db.refresh(profile)
    return profile


def _profile_to_out(profile: Profile) -> ProfileOut:
    """Convert ORM profile + relations to response schema."""
    return ProfileOut(
        id=profile.id,
        full_name=profile.full_name,
        phone=profile.phone,
        email=profile.email,
        location=profile.location,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        hook_line=profile.hook_line,
        allow_ai_projects=profile.allow_ai_projects,
        onboarding_step=profile.onboarding_step,
        is_complete=profile.is_complete,
        educations=[
            EducationOut(id=e.id, degree=e.degree, institution=e.institution, dates=e.dates, sort_order=e.sort_order)
            for e in profile.educations
        ],
        experiences=[
            ExperienceOut(
                id=e.id, title=e.title, company=e.company, location=e.location,
                dates=e.dates, bullets=json.loads(e.bullets_json), sort_order=e.sort_order,
            )
            for e in profile.experiences
        ],
        projects=[
            ProjectOut(
                id=p.id, title=p.title, description=p.description,
                technologies=json.loads(p.technologies_json), url=p.url, sort_order=p.sort_order,
            )
            for p in profile.projects
        ],
        skills=[
            SkillCategoryOut(id=s.id, category=s.category, items=json.loads(s.items_json), sort_order=s.sort_order)
            for s in profile.skills
        ],
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def get_profile(db: AsyncSession, user_id: str) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Basics (Step 2)
# ---------------------------------------------------------------------------


async def update_basics(db: AsyncSession, user_id: str, data: ProfileBasicsIn) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    profile.full_name = data.full_name
    profile.phone = data.phone
    profile.email = data.email
    profile.location = data.location
    profile.linkedin_url = data.linkedin_url
    profile.github_url = data.github_url
    await db.commit()
    await db.refresh(profile)
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Voice (Step 7)
# ---------------------------------------------------------------------------


async def update_voice(db: AsyncSession, user_id: str, data: ProfileVoiceIn) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    profile.hook_line = data.hook_line
    profile.allow_ai_projects = data.allow_ai_projects
    await db.commit()
    await db.refresh(profile)
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Onboarding step
# ---------------------------------------------------------------------------


async def advance_step(db: AsyncSession, user_id: str, step: int) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    profile.onboarding_step = step
    if step >= 8 and profile.completed_at is None:
        profile.completed_at = utcnow()
    await db.commit()
    await db.refresh(profile)
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Education CRUD
# ---------------------------------------------------------------------------


async def set_educations(db: AsyncSession, user_id: str, items: list[EducationIn]) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    # Replace all
    for existing in list(profile.educations):
        await db.delete(existing)
    await db.flush()
    for i, item in enumerate(items):
        edu = Education(
            id=new_uuid(), profile_id=profile.id,
            degree=item.degree, institution=item.institution, dates=item.dates,
            sort_order=i,
        )
        db.add(edu)
    await db.commit()
    # Refresh to load new relations
    await db.refresh(profile, ["educations"])
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Experience CRUD
# ---------------------------------------------------------------------------


async def set_experiences(db: AsyncSession, user_id: str, items: list[ExperienceIn]) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    for existing in list(profile.experiences):
        await db.delete(existing)
    await db.flush()
    for i, item in enumerate(items):
        exp = Experience(
            id=new_uuid(), profile_id=profile.id,
            title=item.title, company=item.company, location=item.location,
            dates=item.dates, bullets_json=json.dumps(item.bullets),
            sort_order=i,
        )
        db.add(exp)
    await db.commit()
    await db.refresh(profile, ["experiences"])
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Projects CRUD
# ---------------------------------------------------------------------------


async def set_projects(db: AsyncSession, user_id: str, items: list[ProjectIn]) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    for existing in list(profile.projects):
        await db.delete(existing)
    await db.flush()
    for i, item in enumerate(items):
        proj = Project(
            id=new_uuid(), profile_id=profile.id,
            title=item.title, description=item.description,
            technologies_json=json.dumps(item.technologies), url=item.url,
            sort_order=i,
        )
        db.add(proj)
    await db.commit()
    await db.refresh(profile, ["projects"])
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Skills CRUD
# ---------------------------------------------------------------------------


async def set_skills(db: AsyncSession, user_id: str, items: list[SkillCategoryIn]) -> ProfileOut:
    profile = await get_or_create_profile(db, user_id)
    for existing in list(profile.skills):
        await db.delete(existing)
    await db.flush()
    for i, item in enumerate(items):
        cat = SkillCategory(
            id=new_uuid(), profile_id=profile.id,
            category=item.category, items_json=json.dumps(item.items),
            sort_order=i,
        )
        db.add(cat)
    await db.commit()
    await db.refresh(profile, ["skills"])
    return _profile_to_out(profile)


# ---------------------------------------------------------------------------
# Build base_resume.json from profile (consumed by the tailoring engine)
# ---------------------------------------------------------------------------


async def build_base_resume_json(db: AsyncSession, user_id: str) -> dict:
    """Assemble the base_resume.json format from the normalized profile tables.

    This is the same format the original resume-tailor project uses:
    {
      "immutable": { "name", "contact", "education" },
      "editable": { "about", "skills", "experience", "projects" }
    }
    """
    profile = await get_or_create_profile(db, user_id)

    return {
        "immutable": {
            "name": profile.full_name or "",
            "contact": {
                "phone": profile.phone or "",
                "email": profile.email or "",
            },
            "education": [
                {
                    "degree": e.degree,
                    "institution": e.institution,
                    "dates": e.dates or "",
                }
                for e in profile.educations
            ],
        },
        "editable": {
            "about": profile.hook_line or "",
            "skills": {
                s.category: json.loads(s.items_json)
                for s in profile.skills
            } if profile.skills else [],
            "experience": [
                {
                    "title": exp.title,
                    "company": exp.company,
                    "location": exp.location or "",
                    "dates": exp.dates or "",
                    "bullets": json.loads(exp.bullets_json),
                }
                for exp in profile.experiences
            ],
            "projects": [
                {
                    "title": p.title,
                    "description": p.description or "",
                    "technologies": json.loads(p.technologies_json),
                }
                for p in profile.projects
            ],
        },
    }
