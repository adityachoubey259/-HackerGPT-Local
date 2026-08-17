"""Public configuration endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.core import get_app_settings
from backend.api.schemas.system import PublicConfigResponse
from backend.core.config import AppSettings
from backend.core.policy import PolicyConfig, load_policy
from backend.services.prompts import response_policy_public

router = APIRouter(tags=["config"])
SettingsDependency = Annotated[AppSettings, Depends(get_app_settings)]


@router.get("/config/public", response_model=PublicConfigResponse)
async def public_config(
    request: Request,
    settings: SettingsDependency,
) -> PublicConfigResponse:
    policy: PolicyConfig | None = getattr(request.app.state, "policy", None)
    if policy is None:
        policy = load_policy()
    return PublicConfigResponse.model_validate(
        settings.public_config() | {"response": response_policy_public(policy)}
    )
