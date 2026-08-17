"""Prompt Architect endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.prompting.models import (
    PromptArchitectRequest,
    PromptArchitectResponse,
    PromptProfile,
)
from backend.services.prompt_architect import PromptArchitectService

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/profiles", response_model=list[PromptProfile])
async def prompt_profiles(request: Request) -> list[PromptProfile]:
    service: PromptArchitectService = request.app.state.prompt_architect_service
    return service.list_profiles()


@router.post("/generate", response_model=PromptArchitectResponse)
async def generate_prompt(
    request: Request,
    body: PromptArchitectRequest,
) -> PromptArchitectResponse:
    service: PromptArchitectService = request.app.state.prompt_architect_service
    return service.generate(body)
