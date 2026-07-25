"""FastAPI dependencies for auth and common request context."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    CSRFError,
    EmailNotVerifiedError,
    TokenInvalidError,
)
from app.core.logging import user_id_ctx
from app.core.security import decode_access_token, validate_csrf
from app.db.models.user import User
from app.db.session import get_session


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Extract and validate the access token from cookies.

    Sets the user_id context var for structured logging.
    Raises AuthenticationError/TokenExpiredError if invalid.
    """
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise AuthenticationError("Not authenticated. Please log in.")

    payload = decode_access_token(token)
    if payload is None:
        raise TokenInvalidError("Invalid session. Please log in again.")

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidError("Malformed token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise TokenInvalidError("User not found.")
    if not user.is_active:
        raise AuthenticationError("Account deactivated.", code="account_deactivated")

    # Attach to context for logging
    user_id_ctx.set(user.id)
    return user


async def get_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require an authenticated AND email-verified user.

    Used by endpoints that perform actions (tailor, billing) but not by
    profile/settings (which you need before verifying).
    """
    if not user.is_email_verified:
        raise EmailNotVerifiedError("Please verify your email before using this feature.")
    return user


async def require_csrf(
    request: Request,
) -> None:
    """CSRF double-submit validation for state-changing requests.

    Skipped for GET/HEAD/OPTIONS and for non-cookie auth (API keys, if added later).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get("X-CSRF-Token")

    if not validate_csrf(cookie_token, header_token):
        raise CSRFError("CSRF token mismatch. Refresh the page and try again.")
