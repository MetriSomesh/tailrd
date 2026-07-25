"""Pydantic schemas for profile and onboarding endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Nested items
# ---------------------------------------------------------------------------


class EducationIn(BaseModel):
    degree: str = Field(min_length=1, max_length=300)
    institution: str = Field(min_length=1, max_length=300)
    dates: str | None = Field(default=None, max_length=100)


class EducationOut(EducationIn):
    id: str
    sort_order: int = 0


class ExperienceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    dates: str | None = Field(default=None, max_length=100)
    bullets: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("bullets")
    @classmethod
    def _clean_bullets(cls, v: list[str]) -> list[str]:
        return [b.strip() for b in v if b.strip()]


class ExperienceOut(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    dates: str | None = None
    bullets: list[str] = []
    sort_order: int = 0


class ProjectIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    url: str | None = Field(default=None, max_length=500)

    @field_validator("technologies")
    @classmethod
    def _clean_tech(cls, v: list[str]) -> list[str]:
        return [t.strip() for t in v if t.strip()]


class ProjectOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    technologies: list[str] = []
    url: str | None = None
    sort_order: int = 0


class SkillCategoryIn(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    items: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("items")
    @classmethod
    def _clean_items(cls, v: list[str]) -> list[str]:
        return [i.strip() for i in v if i.strip()]


class SkillCategoryOut(BaseModel):
    id: str
    category: str
    items: list[str] = []
    sort_order: int = 0


# ---------------------------------------------------------------------------
# Profile top-level
# ---------------------------------------------------------------------------


class ProfileBasicsIn(BaseModel):
    """Step 2: basic contact info."""

    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    location: str | None = Field(default=None, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)


class ProfileVoiceIn(BaseModel):
    """Step 7: hook line + AI projects toggle."""

    hook_line: str | None = Field(default=None, max_length=500)
    allow_ai_projects: bool = False


class ProfileOut(BaseModel):
    """Full profile response."""

    id: str
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    hook_line: str | None = None
    allow_ai_projects: bool = False
    onboarding_step: int = 0
    is_complete: bool = False
    educations: list[EducationOut] = []
    experiences: list[ExperienceOut] = []
    projects: list[ProjectOut] = []
    skills: list[SkillCategoryOut] = []


class OnboardingStepUpdate(BaseModel):
    """Advance onboarding_step after each wizard step is completed."""

    step: int = Field(ge=0, le=8)


# ---------------------------------------------------------------------------
# Resume upload parsing result
# ---------------------------------------------------------------------------


class ParsedResumeResult(BaseModel):
    """Result of parsing an uploaded resume file into structured data."""

    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    educations: list[EducationIn] = []
    experiences: list[ExperienceIn] = []
    projects: list[ProjectIn] = []
    skills: list[SkillCategoryIn] = []
    raw_text: str | None = None
