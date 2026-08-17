"""Local metrics middleware."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.observability import LocalMetrics


class LocalMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        metrics: LocalMetrics | None = getattr(request.app.state, "local_metrics", None)
        if metrics is not None:
            route = f"{request.method} {request.url.path}"
            metrics.record(route, response.status_code, (time.perf_counter() - started) * 1000)
        return response
