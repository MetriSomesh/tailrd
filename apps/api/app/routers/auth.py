"""Auth routes: signup, login, logout, refresh, verify, reset, Google OAuth, /me."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_csrf
from app.core.errors import BadRequestError
from app.core.security import generate_csrf_token
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly auth cookies + a CSRF cookie (readable by JS for headers)."""
    common = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.COOKIE_SECURE,
        "domain": settings.COOKIE_DOMAIN,
    }

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_TTL_SECONDS,
        path="/",
        **common,
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_TTL_SECONDS,
        path="/",  # narrowing to /api/v1/auth/refresh is stricter but complicates the frontend
        **common,
    )
    # CSRF cookie is NOT httpOnly — JS reads it to send in the header.
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=generate_csrf_token(),
        max_age=settings.REFRESH_TOKEN_TTL_SECONDS,
        path="/",
        httponly=False,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in (
        settings.SESSION_COOKIE_NAME,
        settings.REFRESH_COOKIE_NAME,
        settings.CSRF_COOKIE_NAME,
    ):
        response.delete_cookie(name, path="/", domain=settings.COOKIE_DOMAIN)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        auth_provider=user.auth_provider,
        email_verified=user.is_email_verified,
        created_at=user.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    user = await auth_service.signup(
        db,
        email=body.email,
        password=body.password,
        name=body.name,
        ip=request.client.host if request.client else None,
    )
    # Log the user in immediately (unverified — can browse profile but not tailor).
    _, access_token, refresh_token = await auth_service.login(
        db,
        email=body.email,
        password=body.password,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(
        user=_user_to_response(user), message="Account created. Check your email to verify."
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    user, access_token, refresh_token = await auth_service.login(
        db,
        email=body.email,
        password=body.password,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=_user_to_response(user))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
    _csrf: None = Depends(require_csrf),
):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        await auth_service.revoke_session(db, refresh_token=refresh_token)
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise BadRequestError("No refresh token found.")

    user, access_token, new_refresh = await auth_service.refresh_tokens(
        db,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access_token, new_refresh)
    return AuthResponse(user=_user_to_response(user))


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_session),
):
    await auth_service.verify_email(db, token=body.token)
    return MessageResponse(message="Email verified successfully.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_session),
):
    await auth_service.resend_verification(db, email=body.email)
    return MessageResponse(
        message="If that email is registered and unverified, a new link was sent."
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_session),
):
    await auth_service.request_password_reset(db, email=body.email)
    return MessageResponse(message="If that email is registered, a reset link was sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_session),
):
    await auth_service.reset_password(db, token=body.token, new_password=body.password)
    return MessageResponse(message="Password reset. You can now log in with your new password.")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return _user_to_response(user)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/google/start")
async def google_start(request: Request, response: Response):
    """Redirect the user to Google's OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise BadRequestError("Google login is not configured.")

    from app.core.security import generate_token

    state = generate_token(16)
    # Store state in a short-lived cookie for verification on callback.
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.BACKEND_URL}{settings.API_V1_PREFIX}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    from starlette.responses import RedirectResponse

    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    """Exchange the auth code for tokens and create/login the user."""
    import httpx

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.cookies.get("oauth_state")

    if not code or not state or state != stored_state:
        raise BadRequestError("Invalid OAuth callback. Please try again.")

    # Clear the state cookie
    response.delete_cookie("oauth_state")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise BadRequestError("Google login is not configured.")

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.BACKEND_URL}{settings.API_V1_PREFIX}/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        raise BadRequestError("Failed to exchange authorization code.")

    tokens = token_resp.json()
    access_token_google = tokens.get("access_token")
    if not access_token_google:
        raise BadRequestError("No access token from Google.")

    # Fetch user info
    async with httpx.AsyncClient(timeout=10) as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_google}"},
        )

    if userinfo_resp.status_code != 200:
        raise BadRequestError("Failed to fetch Google user info.")

    info = userinfo_resp.json()
    google_id = info.get("sub")
    email = info.get("email")
    name = info.get("name", email.split("@")[0] if email else "User")
    avatar = info.get("picture")

    if not google_id or not email:
        raise BadRequestError("Google did not provide required account info.")

    user, access_tok, refresh_tok, is_new = await auth_service.login_or_create_via_google(
        db,
        google_id=google_id,
        email=email,
        name=name,
        avatar_url=avatar,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    _set_auth_cookies(response, access_tok, refresh_tok)

    # Redirect to frontend — the cookies are set, the frontend reads /me on load.
    redirect_path = "/onboarding" if is_new else "/dashboard"
    from starlette.responses import RedirectResponse

    return RedirectResponse(url=f"{settings.FRONTEND_URL}{redirect_path}", status_code=302)
