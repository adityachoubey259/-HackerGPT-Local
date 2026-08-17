"""Application and API error handling."""

from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.logging import get_logger

logger = get_logger(__name__)


class ApplicationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        }
    }


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    logger.warning(
        "application_error",
        code=exc.code,
        request_id=_request_id(request),
        route=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=exc.details,
        ),
    )


async def http_error_handler(
    request: Request, exc: HTTPException | StarletteHTTPException
) -> JSONResponse:
    code = "HTTP_ERROR" if exc.status_code < 500 else "INTERNAL_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            code=code,
            message=str(exc.detail),
            request_id=_request_id(request),
        ),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_payload(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=_request_id(request),
            details={"errors": exc.errors()},
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    settings = request.app.state.settings
    logger.exception(
        "unhandled_exception",
        request_id=_request_id(request),
        route=str(request.url.path),
    )
    details: dict[str, Any] = {}
    message = "Internal server error."
    if settings.debug:
        details["exception_type"] = exc.__class__.__name__
        message = str(exc) or message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            code="INTERNAL_ERROR",
            message=message,
            request_id=_request_id(request),
            details=details,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, cast(Any, application_error_handler))
    app.add_exception_handler(HTTPException, cast(Any, http_error_handler))
    app.add_exception_handler(StarletteHTTPException, cast(Any, http_error_handler))
    app.add_exception_handler(RequestValidationError, cast(Any, validation_error_handler))
    app.add_exception_handler(Exception, unhandled_error_handler)
