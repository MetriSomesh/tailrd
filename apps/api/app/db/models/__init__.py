"""SQLAlchemy models.

Imported here so Alembic autogenerate and Base.metadata.create_all see every
table without callers needing to know module layout.
"""

from app.db.models.consent import ConsentRecord
from app.db.models.profile import Education, Experience, Profile, Project, SkillCategory
from app.db.models.run import TailorRun
from app.db.models.token import EmailToken
from app.db.models.user import AuthProvider, OAuthAccount, Session, User

__all__ = [
    "AuthProvider",
    "ConsentRecord",
    "Education",
    "EmailToken",
    "Experience",
    "OAuthAccount",
    "Profile",
    "Project",
    "Session",
    "SkillCategory",
    "TailorRun",
    "User",
]
