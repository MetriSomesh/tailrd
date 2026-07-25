"""Tests for auth endpoints: signup, login, logout, refresh, verify, reset, /me."""

from __future__ import annotations

from httpx import AsyncClient


class TestSignup:
    async def test_signup_creates_user_and_sets_cookies(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": "strongPass123!", "name": "Test User"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["user"]["email"] == "test@example.com"
        assert body["user"]["name"] == "Test User"
        assert body["user"]["email_verified"] is False
        # Auth cookies should be set
        assert "tailrd_at" in r.cookies
        assert "tailrd_rt" in r.cookies
        assert "tailrd_csrf" in r.cookies

    async def test_signup_rejects_duplicate_email(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "dup@example.com", "password": "strongPass123!", "name": "User1"},
        )
        r = await client.post(
            "/api/v1/auth/signup",
            json={"email": "dup@example.com", "password": "otherPass999!", "name": "User2"},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "email_already_registered"

    async def test_signup_validates_weak_password(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/signup",
            json={"email": "weak@example.com", "password": "aaaaaaa1", "name": "Weak"},
        )
        assert r.status_code == 422

    async def test_signup_validates_short_password(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/signup",
            json={"email": "short@example.com", "password": "Ab1!", "name": "Short"},
        )
        assert r.status_code == 422

    async def test_signup_validates_email_format(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "strongPass123!", "name": "Invalid"},
        )
        assert r.status_code == 422


class TestLogin:
    async def test_login_with_correct_credentials(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "login@example.com", "password": "mySecret42!", "name": "Login User"},
        )
        # Clear cookies from signup
        client.cookies.clear()

        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "mySecret42!"},
        )
        assert r.status_code == 200
        assert r.json()["user"]["email"] == "login@example.com"
        assert "tailrd_at" in r.cookies

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "wrong@example.com", "password": "correct123!", "name": "Wrong"},
        )
        client.cookies.clear()

        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect!"},
        )
        assert r.status_code == 401
        assert r.json()["code"] == "invalid_credentials"

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "anything123!"},
        )
        assert r.status_code == 401
        assert r.json()["code"] == "invalid_credentials"


class TestMe:
    async def test_me_returns_user_when_authenticated(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "me@example.com", "password": "secret1234!", "name": "Me User"},
        )
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "me@example.com"

    async def test_me_returns_401_without_cookie(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestRefresh:
    async def test_refresh_rotates_tokens(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "refresh@example.com", "password": "secret1234!", "name": "Refresh"},
        )
        old_at = client.cookies.get("tailrd_at")
        old_rt = client.cookies.get("tailrd_rt")

        r = await client.post("/api/v1/auth/refresh")
        assert r.status_code == 200

        new_at = r.cookies.get("tailrd_at")
        new_rt = r.cookies.get("tailrd_rt")
        # Tokens should have changed
        assert new_at != old_at or new_rt != old_rt

    async def test_refresh_without_cookie_fails(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/auth/refresh")
        assert r.status_code == 400


class TestLogout:
    async def test_logout_clears_cookies(self, client: AsyncClient) -> None:
        # Signup (sets cookies)
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "logout@example.com", "password": "secret1234!", "name": "Logout"},
        )
        # Get the CSRF token from cookies
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200


class TestPasswordReset:
    async def test_forgot_password_always_200(self, client: AsyncClient) -> None:
        # Doesn't reveal if email exists
        r = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert r.status_code == 200

    async def test_reset_with_invalid_token_fails(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "a" * 43, "password": "newStrong567!"},
        )
        assert r.status_code == 401  # TokenInvalidError


class TestAccountExport:
    async def test_export_returns_user_data(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "export@example.com", "password": "secret1234!", "name": "Export User"},
        )
        r = await client.get("/api/v1/account/export")
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == "export@example.com"
        assert data["export_version"] == "1.0"
        assert "consent_records" in data

    async def test_export_requires_auth(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/account/export")
        assert r.status_code == 401


class TestAccountDeletion:
    async def test_delete_marks_account(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "delete@example.com", "password": "secret1234!", "name": "Delete User"},
        )
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.delete(
            "/api/v1/account",
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200
        assert "scheduled for deletion" in r.json()["message"]
