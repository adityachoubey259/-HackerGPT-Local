"""API authentication middleware."""

from __future__ import annotations

from fastapi import Request
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from backend.api.errors import error_payload
from backend.auth.service import AuthService

PUBLIC_API_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/health",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        service: AuthService | None = getattr(request.app.state, "auth_service", None)
        if service is None or not service.enabled or _is_public(request.url.path):
            return await call_next(request)
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        user = await service.user_from_token(request.cookies.get(service.cookie_name))
        if user is None:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_payload(
                    code="AUTH_REQUIRED",
                    message="Authentication required.",
                    request_id=request_id,
                ),
            )
        request.state.auth_user = user
        return await call_next(request)


def _is_public(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)
