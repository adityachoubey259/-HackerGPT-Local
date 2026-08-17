"""Agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from starlette import status

from backend.agents.models import AgentCreate, AgentDefinition, AgentPatch
from backend.services.agents import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDefinition])
async def list_agents(request: Request) -> list[AgentDefinition]:
    service: AgentService = request.app.state.agent_service
    return await service.list_agents()


@router.post("", response_model=AgentDefinition, status_code=status.HTTP_201_CREATED)
async def create_agent(request: Request, body: AgentCreate) -> AgentDefinition:
    service: AgentService = request.app.state.agent_service
    return await service.create(body)


@router.get("/{agent_id}", response_model=AgentDefinition)
async def get_agent(request: Request, agent_id: str) -> AgentDefinition:
    service: AgentService = request.app.state.agent_service
    return await service.get_agent(agent_id)


@router.patch("/{agent_id}", response_model=AgentDefinition)
async def patch_agent(request: Request, agent_id: str, body: AgentPatch) -> AgentDefinition:
    service: AgentService = request.app.state.agent_service
    return await service.patch(agent_id, body)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_agent(request: Request, agent_id: str) -> Response:
    service: AgentService = request.app.state.agent_service
    await service.delete(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{agent_id}/duplicate",
    response_model=AgentDefinition,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_agent(request: Request, agent_id: str) -> AgentDefinition:
    service: AgentService = request.app.state.agent_service
    return await service.duplicate(agent_id)
