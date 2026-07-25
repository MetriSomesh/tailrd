"""Request middleware: correlation IDs, timing, body-size guard, security headers."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger, request_id_ctx

log = get_logger(__name__)

REQUEST_ID_HEADER = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, log the request, and never let an error escape raw."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The exception handlers below normally catch this. This is the
            # last line of defence so a middleware-level failure still yields
            # a well-formed response instead of a dropped connection.
            duration_ms = (time.perf_counter() - started) * 1000
            log.exception(
                "request_failed_unhandled",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            request_id_ctx.reset(token)
            return JSONResponse(
                status_code=500,
                content={
                    "type": "https://tailrd.app/errors/internal_error",
                    "title": "Internal Server Error",
                    "status": 500,
                    "code": "internal_error",
                    "detail": "An unexpected error occurred.",
                    "request_id": request_id,
                },
                media_type="application/problem+json",
                headers={REQUEST_ID_HEADER: request_id},
            )

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id

        # Skip access logs for probes to keep the log signal clean.
        if request.url.path not in ("/health", "/ready", "/metrics"):
            log.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        request_id_ctx.reset(token)
        return response


class BodySizeLimitMiddleware:
    """Reject oversized bodies early, before they are buffered into memory.

    Critical on a 1 GB host: an unbounded upload can OOM the process.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw_len = headers.get(b"content-length")
        if raw_len is not None:
            try:
                if int(raw_len) > self.max_bytes:
                    await self._too_large(send)
                    return
            except ValueError:
                pass

        received = 0
        too_large = False

        async def guarded_receive():
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b"") or b"")
                if received > self.max_bytes:
                    too_large = True
                    # Signal end of stream so the app doesn't hang.
                    return {"type": "http.disconnect"}
            return message

        if too_large:
            await self._too_large(send)
            return

        await self.app(scope, guarded_receive, send)

    async def _too_large(self, send) -> None:
        body = (
            b'{"type":"https://tailrd.app/errors/payload_too_large",'
            b'"title":"Payload Too Large","status":413,'
            b'"code":"payload_too_large",'
            b'"detail":"Request body exceeds the maximum allowed size."}'
        )
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defence-in-depth headers.

    Caddy sets these at the edge in production too; doing it here means local
    dev and any direct-to-app traffic get the same protection.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        # The API only ever returns JSON; a restrictive CSP is free here.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        return response
