"""Authenticated user preference endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.api.schemas.preferences import UserPreferencesPatch, UserPreferencesResponse
from backend.auth.service import AuthenticatedUser
from backend.db.repositories.sqlalchemy import LOCAL_USER_ID
from backend.services.preferences import PreferenceService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=UserPreferencesResponse)
async def get_preferences(request: Request) -> UserPreferencesResponse:
    service: PreferenceService = request.app.state.preference_service
    return await service.get(_user_id(request))


@router.patch("", response_model=UserPreferencesResponse)
async def patch_preferences(
    request: Request,
    body: UserPreferencesPatch,
) -> UserPreferencesResponse:
    service: PreferenceService = request.app.state.preference_service
    return await service.patch(_user_id(request), body)


def _user_id(request: Request) -> str:
    user = getattr(request.state, "auth_user", None)
    if isinstance(user, AuthenticatedUser):
        return user.id
    return LOCAL_USER_ID
