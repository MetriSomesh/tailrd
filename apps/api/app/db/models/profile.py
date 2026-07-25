"""Profile models: normalized resume data for the onboarding wizard.

Stored as separate tables (not a single JSON blob) so we can:
- Validate individual entries
- Reorder via sort_order
- Partially save during onboarding without losing progress
- Query skills across users for analytics
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Profile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core profile: one per user. Created at signup, populated during onboarding."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(320))
    location: Mapped[str | None] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    hook_line: Mapped[str | None] = mapped_column(Text)
    allow_ai_projects: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Onboarding progress: 0 = not started, 8 = complete
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships (selectin = eager load with the parent query, avoids greenlet issues)
    educations: Mapped[list[Education]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Education.sort_order",
        lazy="selectin",
    )
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Experience.sort_order",
        lazy="selectin",
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Project.sort_order",
        lazy="selectin",
    )
    skills: Mapped[list[SkillCategory]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="SkillCategory.sort_order",
        lazy="selectin",
    )

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


class Education(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "educations"

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    degree: Mapped[str] = mapped_column(String(300), nullable=False)
    institution: Mapped[str] = mapped_column(String(300), nullable=False)
    dates: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="educations")


class Experience(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "experiences"

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    dates: Mapped[str | None] = mapped_column(String(100))
    # Stored as JSON array string for SQLite compat; parsed in the schema layer.
    bullets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="experiences")


class Project(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "projects"

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Stored as JSON array string.
    technologies_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="projects")


class SkillCategory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "skill_categories"

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # Stored as JSON array string.
    items_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="skills")
