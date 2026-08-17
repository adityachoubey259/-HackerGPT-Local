"""Request correlation and access logging middleware."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
logger = get_logger(__name__)


def _safe_request_id(value: str | None) -> str:
    if value is None:
        return str(uuid.uuid4())
    candidate = value.strip()
    if 1 <= len(candidate) <= 128 and all(char.isalnum() or char in "-_." for char in candidate):
        return candidate
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _safe_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            logger.info(
                "request_completed",
                method=request.method,
                route=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()


class RequestIdResponseHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = getattr(request.state, "request_id", "unknown")
        return response
