"""Local authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from starlette import status

from backend.api.errors import ApplicationError
from backend.api.schemas.auth import (
    AuthSessionResponse,
    AuthUserResponse,
    ChangePasswordRequest,
    LoginRequest,
)
from backend.auth.service import AuthenticatedUser, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthSessionResponse)
async def login(request: Request, response: Response, body: LoginRequest) -> AuthSessionResponse:
    service: AuthService = request.app.state.auth_service
    user = await service.authenticate(body.username, body.password)
    if user is None:
        raise ApplicationError(
            "AUTH_INVALID_CREDENTIALS",
            "Invalid username or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = service.create_session_token(user)
    response.set_cookie(
        service.cookie_name,
        token,
        max_age=service.ttl_seconds,
        httponly=True,
        secure=service.cookie_secure,
        samesite=service.cookie_samesite,
        path="/",
    )
    return AuthSessionResponse(authenticated=True, user=_user_response(user))


@router.post("/logout", response_model=AuthSessionResponse)
async def logout(request: Request, response: Response) -> AuthSessionResponse:
    service: AuthService = request.app.state.auth_service
    response.delete_cookie(service.cookie_name, path="/")
    return AuthSessionResponse(authenticated=False, user=None)


@router.post("/change-password", response_model=AuthSessionResponse)
async def change_password(
    request: Request,
    response: Response,
    body: ChangePasswordRequest,
) -> AuthSessionResponse:
    service: AuthService = request.app.state.auth_service
    user = getattr(request.state, "auth_user", None)
    if not isinstance(user, AuthenticatedUser):
        user = await service.user_from_token(request.cookies.get(service.cookie_name))
    if not isinstance(user, AuthenticatedUser):
        raise ApplicationError(
            "AUTH_REQUIRED",
            "Authentication required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    changed = await service.change_password(user.id, body.current_password, body.new_password)
    if changed is None:
        raise ApplicationError(
            "AUTH_PASSWORD_CHANGE_FAILED",
            "Current password is invalid or the new password is not allowed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    token = service.create_session_token(changed)
    response.set_cookie(
        service.cookie_name,
        token,
        max_age=service.ttl_seconds,
        httponly=True,
        secure=service.cookie_secure,
        samesite=service.cookie_samesite,
        path="/",
    )
    return AuthSessionResponse(authenticated=True, user=_user_response(changed))


@router.get("/me", response_model=AuthSessionResponse)
async def me(request: Request) -> AuthSessionResponse:
    user = getattr(request.state, "auth_user", None)
    if isinstance(user, AuthenticatedUser):
        return AuthSessionResponse(authenticated=True, user=_user_response(user))
    service: AuthService = request.app.state.auth_service
    user = await service.user_from_token(request.cookies.get(service.cookie_name))
    if user is None:
        return AuthSessionResponse(authenticated=False, user=None)
    return AuthSessionResponse(authenticated=True, user=_user_response(user))


def _user_response(user: AuthenticatedUser) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_bootstrap=user.is_bootstrap,
    )
