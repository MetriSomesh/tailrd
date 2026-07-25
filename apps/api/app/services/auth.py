"""Auth service: signup, login, token lifecycle, Google OAuth.

Orchestrates database operations, hashing, email, and token generation.
Keeps the router layer thin (validation + cookies only).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    NotFoundError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_token,
    hash_ip,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.db.base import new_uuid, utcnow
from app.db.models.consent import ConsentRecord
from app.db.models.token import EmailToken
from app.db.models.user import AuthProvider, OAuthAccount, Session, User
from app.services.email import (
    get_email_provider,
    render_password_reset_email,
    render_verification_email,
)

log = get_logger(__name__)

CURRENT_POLICY_VERSION = "2024-01-01"


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


async def signup(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    name: str,
    ip: str | None = None,
) -> User:
    """Create a new user with email/password auth.

    Sends a verification email. Does NOT auto-verify.
    """
    # Check for existing user
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    user = User(
        id=new_uuid(),
        email=email.lower().strip(),
        name=name.strip(),
        password_hash=hash_password(password),
        auth_provider=AuthProvider.EMAIL.value,
    )
    db.add(user)

    # DPDP consent record
    consent = ConsentRecord(
        user_id=user.id,
        policy_version=CURRENT_POLICY_VERSION,
        ip_hash=hash_ip(ip),
    )
    db.add(consent)

    await db.flush()

    # Send verification email
    await _send_verification_email(db, user)

    await db.commit()
    log.info("user_signup", user_id=user.id, provider="email")
    return user


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


async def _send_verification_email(db: AsyncSession, user: User) -> None:
    """Generate a verification token and send the email."""
    raw_token = generate_token()
    expires = utcnow() + timedelta(seconds=settings.EMAIL_VERIFY_TTL_SECONDS)

    token_record = EmailToken(
        email=user.email,
        token_hash=hash_token(raw_token),
        purpose="verify",
        expires_at=expires,
    )
    db.add(token_record)
    await db.flush()

    verify_url = f"{settings.FRONTEND_URL}/verify?token={raw_token}"
    subject, html = render_verification_email(user.name, verify_url)
    provider = get_email_provider()
    await provider.send(user.email, subject, html)


async def verify_email(db: AsyncSession, *, token: str) -> User:
    """Consume a verification token and mark the user's email as verified."""
    token_hash = hash_token(token)
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == "verify",
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise TokenInvalidError("Invalid or already used verification link.")
    if token_record.is_used:
        raise TokenInvalidError("This verification link has already been used.")
    if token_record.is_expired:
        raise TokenExpiredError("This verification link has expired. Request a new one.")

    # Mark token as used
    token_record.used_at = utcnow()

    # Verify the user
    user_result = await db.execute(select(User).where(User.email == token_record.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found.")

    user.email_verified_at = utcnow()
    await db.commit()

    log.info("email_verified", user_id=user.id)
    return user


async def resend_verification(db: AsyncSession, *, email: str) -> None:
    """Resend the verification email if the user exists and is unverified."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user or user.is_email_verified:
        # Don't reveal whether the user exists.
        return

    await _send_verification_email(db, user)
    await db.commit()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[User, str, str]:
    """Authenticate by email/password, return (user, access_token, refresh_token).

    Raises InvalidCredentialsError on bad email or password (same error for both
    to prevent user enumeration).
    """
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        # Constant-time: hash a dummy so timing doesn't reveal whether the user exists.
        verify_password("dummy", hash_password("dummy"))
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.", code="account_deactivated")

    # Rehash if parameters changed
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    access_token = create_access_token(user.id)
    refresh_token = await _create_session(db, user_id=user.id, user_agent=user_agent, ip=ip)

    await db.commit()
    log.info("user_login", user_id=user.id, provider="email")
    return user, access_token, refresh_token


# ---------------------------------------------------------------------------
# Session / refresh token management
# ---------------------------------------------------------------------------


async def _create_session(
    db: AsyncSession,
    *,
    user_id: str,
    user_agent: str | None,
    ip: str | None,
    family_id: str | None = None,
) -> str:
    """Create a new session with a fresh refresh token. Returns the raw token."""
    raw_token = generate_token()
    expires = utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS)

    session = Session(
        user_id=user_id,
        refresh_token_hash=hash_token(raw_token),
        user_agent=user_agent,
        ip_hash=hash_ip(ip),
        expires_at=expires,
        family_id=family_id or new_uuid(),
    )
    db.add(session)
    await db.flush()
    return raw_token


async def refresh_tokens(
    db: AsyncSession,
    *,
    refresh_token: str,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[User, str, str]:
    """Rotate a refresh token: invalidate the old, issue new access + refresh.

    Implements reuse detection: if a revoked token is presented, all sessions
    in that family are revoked (the user's device was likely compromised).
    """
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(Session).where(Session.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise TokenInvalidError("Invalid refresh token.")

    # Reuse detection: if already revoked, someone stole and replayed it.
    if session.is_revoked:
        log.warning("refresh_token_reuse_detected", family_id=session.family_id)
        await _revoke_family(db, session.family_id)
        await db.commit()
        raise TokenInvalidError("Session invalidated for security. Please log in again.")

    if session.is_expired:
        raise TokenExpiredError("Session expired. Please log in again.")

    # Revoke current session
    session.revoked_at = utcnow()

    # Load user
    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthenticationError("Account not found or deactivated.")

    # Issue new tokens in the same family
    access_token = create_access_token(user.id)
    new_refresh = await _create_session(
        db, user_id=user.id, user_agent=user_agent, ip=ip, family_id=session.family_id
    )

    await db.commit()
    return user, access_token, new_refresh


async def _revoke_family(db: AsyncSession, family_id: str) -> None:
    """Revoke all sessions in a token family (reuse detection response)."""
    result = await db.execute(
        select(Session).where(Session.family_id == family_id, Session.revoked_at.is_(None))
    )
    for session in result.scalars():
        session.revoked_at = utcnow()


async def revoke_session(db: AsyncSession, *, refresh_token: str) -> None:
    """Explicitly revoke a single session (logout)."""
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(Session).where(Session.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if session and not session.is_revoked:
        session.revoked_at = utcnow()
        await db.commit()


async def revoke_all_sessions(db: AsyncSession, *, user_id: str) -> int:
    """Revoke all active sessions for a user (password change, account delete)."""
    result = await db.execute(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    )
    count = 0
    for session in result.scalars():
        session.revoked_at = utcnow()
        count += 1
    await db.commit()
    return count


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


async def request_password_reset(db: AsyncSession, *, email: str) -> None:
    """Send a password reset email if the user exists.

    Never reveals whether the email is registered (always returns success).
    """
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        return

    raw_token = generate_token()
    expires = utcnow() + timedelta(seconds=settings.PASSWORD_RESET_TTL_SECONDS)

    token_record = EmailToken(
        email=user.email,
        token_hash=hash_token(raw_token),
        purpose="reset",
        expires_at=expires,
    )
    db.add(token_record)
    await db.flush()

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    subject, html = render_password_reset_email(user.name, reset_url)
    provider = get_email_provider()
    await provider.send(user.email, subject, html)
    await db.commit()


async def reset_password(db: AsyncSession, *, token: str, new_password: str) -> User:
    """Consume a reset token and set a new password."""
    token_hash = hash_token(token)
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == "reset",
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise TokenInvalidError("Invalid or already used reset link.")
    if token_record.is_used:
        raise TokenInvalidError("This reset link has already been used.")
    if token_record.is_expired:
        raise TokenExpiredError("This reset link has expired. Request a new one.")

    token_record.used_at = utcnow()

    user_result = await db.execute(select(User).where(User.email == token_record.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found.")

    user.password_hash = hash_password(new_password)
    # Revoke all sessions: forces re-login on all devices.
    await revoke_all_sessions(db, user_id=user.id)

    await db.commit()
    log.info("password_reset", user_id=user.id)
    return user


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


async def login_or_create_via_google(
    db: AsyncSession,
    *,
    google_id: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[User, str, str, bool]:
    """Handle Google OAuth callback. Returns (user, access, refresh, is_new_user).

    If the email already exists (from email signup), links the Google account.
    """
    email = email.lower().strip()

    # Check if we already have this Google account linked
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_account_id == google_id,
        )
    )
    oauth = result.scalar_one_or_none()

    is_new = False

    if oauth:
        # Existing OAuth link: load the user
        user_result = await db.execute(select(User).where(User.id == oauth.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("Account not found or deactivated.")
    else:
        # Check if the email matches an existing user (link accounts)
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if not user:
            # New user via Google
            user = User(
                id=new_uuid(),
                email=email,
                name=name,
                avatar_url=avatar_url,
                auth_provider=AuthProvider.GOOGLE.value,
                email_verified_at=utcnow(),  # Google emails are pre-verified
            )
            db.add(user)

            consent = ConsentRecord(
                user_id=user.id,
                policy_version=CURRENT_POLICY_VERSION,
                ip_hash=hash_ip(ip),
            )
            db.add(consent)
            is_new = True

        # Link Google account
        link = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id=google_id,
        )
        db.add(link)

        # Mark email as verified if it wasn't already
        if not user.email_verified_at:
            user.email_verified_at = utcnow()

    await db.flush()

    access_token = create_access_token(user.id)
    refresh_token = await _create_session(db, user_id=user.id, user_agent=user_agent, ip=ip)

    await db.commit()
    log.info("user_login", user_id=user.id, provider="google", is_new=is_new)
    return user, access_token, refresh_token, is_new
