"""SQLAlchemy models.

Imported here so Alembic autogenerate and Base.metadata.create_all see every
table without callers needing to know module layout.
"""

from app.db.models.consent import ConsentRecord
from app.db.models.token import EmailToken
from app.db.models.user import AuthProvider, OAuthAccount, Session, User

__all__ = [
    "AuthProvider",
    "ConsentRecord",
    "EmailToken",
    "OAuthAccount",
    "Session",
    "User",
]
