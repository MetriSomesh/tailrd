"""Email delivery abstraction.

Two providers:
- console: prints the email to stdout (local dev / tests)
- resend: real transactional delivery via Resend API

The caller never knows which provider is active. Adding SendGrid, SES, or
Postmark later is one file and one config value.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        *,
        text: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send an email. Returns True on success, False on failure.

        Never raises — email delivery failure should degrade the UX (show a
        warning) not crash the request.
        """
        ...


class ConsoleEmailProvider(EmailProvider):
    """Prints emails to stdout. Perfect for local dev."""

    async def send(
        self, to: str, subject: str, html: str, *, text: str | None = None, reply_to: str | None = None
    ) -> bool:
        log.info(
            "email_sent_console",
            to=to,
            subject=subject,
            html_length=len(html),
        )
        print(f"\n{'='*60}")
        print(f"  TO:      {to}")
        print(f"  SUBJECT: {subject}")
        print(f"  FROM:    {settings.EMAIL_FROM}")
        if reply_to:
            print(f"  REPLY:   {reply_to}")
        print(f"{'='*60}")
        print(text or html)
        print(f"{'='*60}\n")
        return True


class ResendEmailProvider(EmailProvider):
    """Real delivery via Resend (https://resend.com)."""

    BASE_URL = "https://api.resend.com"

    async def send(
        self, to: str, subject: str, html: str, *, text: str | None = None, reply_to: str | None = None
    ) -> bool:
        if not settings.RESEND_API_KEY:
            log.error("resend_api_key_missing")
            return False

        payload: dict[str, Any] = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/emails",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code in (200, 201):
                log.info("email_sent_resend", to=to, subject=subject)
                return True
            log.error(
                "resend_send_failed",
                status=resp.status_code,
                body=resp.text[:500],
                to=to,
            )
            return False
        except httpx.HTTPError as exc:
            log.error("resend_http_error", error=str(exc)[:300], to=to)
            return False


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "resend":
        return ResendEmailProvider()
    return ConsoleEmailProvider()


# ---------------------------------------------------------------------------
# Email templates (minimal inline HTML; replaced with a template engine if
# the email count grows beyond ~5 types)
# ---------------------------------------------------------------------------


def _base_wrapper(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a2e; padding: 32px; max-width: 560px; margin: 0 auto;">
{content}
<hr style="border:none; border-top:1px solid #e5e5e5; margin:32px 0 16px">
<p style="font-size:12px; color:#888;">Tailrd · AI resume tailoring</p>
</body>
</html>"""


def render_verification_email(name: str, verify_url: str) -> tuple[str, str]:
    """Returns (subject, html) for the email verification email."""
    subject = "Verify your Tailrd account"
    html = _base_wrapper(f"""
<h2 style="margin:0 0 16px">Welcome, {name}</h2>
<p>Click the button below to verify your email and get started.</p>
<p style="margin:24px 0">
  <a href="{verify_url}" style="display:inline-block; background:#b5690d; color:#fff; padding:12px 24px; border-radius:6px; text-decoration:none; font-weight:500;">
    Verify email
  </a>
</p>
<p style="font-size:13px; color:#666;">
  Or copy this link:<br>
  <a href="{verify_url}" style="color:#b5690d; word-break:break-all;">{verify_url}</a>
</p>
<p style="font-size:12px; color:#999; margin-top:24px;">
  This link expires in 24 hours. If you didn't sign up, ignore this email.
</p>
""")
    return subject, html


def render_password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    """Returns (subject, html) for the password reset email."""
    subject = "Reset your Tailrd password"
    html = _base_wrapper(f"""
<h2 style="margin:0 0 16px">Password reset</h2>
<p>Hi {name}, we received a request to reset your password.</p>
<p style="margin:24px 0">
  <a href="{reset_url}" style="display:inline-block; background:#b5690d; color:#fff; padding:12px 24px; border-radius:6px; text-decoration:none; font-weight:500;">
    Reset password
  </a>
</p>
<p style="font-size:13px; color:#666;">
  Or copy this link:<br>
  <a href="{reset_url}" style="color:#b5690d; word-break:break-all;">{reset_url}</a>
</p>
<p style="font-size:12px; color:#999; margin-top:24px;">
  This link expires in 1 hour. If you didn't request this, your account is safe — just ignore this email.
</p>
""")
    return subject, html
