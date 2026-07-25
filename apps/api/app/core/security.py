"""Cryptographic primitives for auth: hashing, tokens, JWT, CSRF.

Design decisions:
- Argon2id for passwords: memory-hard, resistant to GPU/ASIC attacks.
- SHA-256 for refresh token hashing: speed is fine here because the raw token
  is a 256-bit random value (no dictionary attack surface).
- JWT with HS256 for access tokens: stateless, 15-min TTL, validated per-request.
  We don't use RS256 because there's only one API server; no cross-service
  verification needed.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Tuned for ~250ms on a t3.micro. Increase time_cost for beefier hardware.
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Hash a password with Argon2id. Returns the PHC-format hash string."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against an Argon2id hash. Constant-time."""
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError, HashingError) as exc:
        log.warning("password_verify_error", error=type(exc).__name__)
        return False


def password_needs_rehash(hashed: str) -> bool:
    """Check if the hash parameters are outdated and need upgrading on login."""
    return _ph.check_needs_rehash(hashed)


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------


def generate_token(nbytes: int = 32) -> str:
    """Generate a URL-safe random token (256 bits by default)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 hash a token for storage. One-way, deterministic."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Returns the payload dict on success, None on any failure (expired, tampered,
    wrong type). Never raises — callers check for None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# CSRF double-submit token
# ---------------------------------------------------------------------------


def generate_csrf_token() -> str:
    """Generate a CSRF token to be set as a cookie and included in headers."""
    return secrets.token_urlsafe(32)


def validate_csrf(cookie_token: str | None, header_token: str | None) -> bool:
    """Validate CSRF double-submit: cookie value must match header value.

    Uses hmac.compare_digest for timing-attack resistance.
    """
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


# ---------------------------------------------------------------------------
# IP hashing (DPDP: we store hashed IPs, never raw)
# ---------------------------------------------------------------------------


def hash_ip(ip: str | None) -> str | None:
    """One-way hash an IP address for storage (DPDP compliance).

    Uses HMAC-SHA256 keyed with SECRET_KEY so the hashes can't be reversed
    without the secret, but are still consistent for comparison.
    """
    if not ip:
        return None
    return hmac.HMAC(
        settings.SECRET_KEY[:32].encode(),
        ip.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
