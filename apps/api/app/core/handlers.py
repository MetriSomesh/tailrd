"""Global exception handlers.

Guarantees every failure path returns a well-formed Problem Details JSON body
and never a stack trace.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, DatabaseUnavailableError, InternalError
from app.core.logging import get_logger

log = get_logger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"


def _problem_response(
    request: Request, err: AppError, *, log_level: str = "warning"
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    problem = err.to_problem(instance=str(request.url.path))
    if request_id:
        problem["request_id"] = request_id

    headers: dict[str, str] = {}
    if err.retry_after is not None:
        headers["Retry-After"] = str(err.retry_after)

    getattr(log, log_level)(
        "app_error",
        code=err.code,
        status=err.status_code,
        detail=err.detail,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=err.status_code,
        content=problem,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers or None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        level = "error" if exc.status_code >= 500 else "warning"
        return _problem_response(request, exc, log_level=level)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Normalise Pydantic's error list into something a form can consume.
        fields: list[dict[str, str]] = []
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", []) if p not in ("body", "query", "path")]
            fields.append(
                {
                    "field": ".".join(loc) or "_root",
                    "message": e.get("msg", "Invalid value"),
                    "type": e.get("type", "invalid"),
                }
            )
        err = AppError(
            "One or more fields are invalid.",
            code="validation_error",
            status_code=422,
            extra={"errors": fields},
        )
        err.title = "Validation Failed"
        return _problem_response(request, err)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            400: "bad_request",
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            413: "payload_too_large",
            415: "unsupported_media_type",
            429: "rate_limited",
        }
        code = code_map.get(exc.status_code, f"http_{exc.status_code}")
        err = AppError(
            str(exc.detail) if exc.detail else "Request failed.",
            code=code,
            status_code=exc.status_code,
        )
        err.title = code.replace("_", " ").title()
        level = "error" if exc.status_code >= 500 else "info"
        return _problem_response(request, err, log_level=level)

    @app.exception_handler(OperationalError)
    async def _handle_db_operational(request: Request, exc: OperationalError) -> JSONResponse:
        # Connection refused / pool exhausted / statement timeout.
        log.error("database_operational_error", error=str(exc.orig or exc)[:500])
        return _problem_response(
            request,
            DatabaseUnavailableError(
                "The database is temporarily unavailable. Please retry shortly.",
                retry_after=5,
            ),
            log_level="error",
        )

    @app.exception_handler(DBAPIError)
    async def _handle_dbapi(request: Request, exc: DBAPIError) -> JSONResponse:
        log.error("database_error", error=str(exc.orig or exc)[:500])
        return _problem_response(
            request,
            DatabaseUnavailableError(
                "A database error occurred. Please retry shortly.", retry_after=5
            ),
            log_level="error",
        )

    @app.exception_handler(SQLAlchemyError)
    async def _handle_sqlalchemy(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("sqlalchemy_error")
        return _problem_response(request, InternalError(), log_level="error")

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Never leak the exception message or type to the client.
        log.exception(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            path=request.url.path,
        )
        return _problem_response(request, InternalError(), log_level="error")
