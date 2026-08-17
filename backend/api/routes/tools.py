"""Secure tool endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.api.schemas.tools import (
    ToolConfirmationActionResponse,
    ToolConfirmationRead,
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolExecutionListResponse,
    ToolExecutionRead,
    ToolListResponse,
)
from backend.services.tools import ToolService, confirmation_to_read, execution_to_read

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools(request: Request) -> ToolListResponse:
    service: ToolService = request.app.state.tool_service
    return ToolListResponse(items=service.list_tools())


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: Request, body: ToolExecuteRequest) -> ToolExecuteResponse:
    service: ToolService = request.app.state.tool_service
    request_id = getattr(request.state, "request_id", "unknown")
    return await service.execute(
        tool_name=body.tool_name,
        arguments=body.arguments,
        agent_id=body.agent_id,
        conversation_id=body.conversation_id,
        request_id=request_id,
    )


@router.get("/executions", response_model=ToolExecutionListResponse)
async def tool_history(
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ToolExecutionListResponse:
    service: ToolService = request.app.state.tool_service
    return await service.history(limit=limit, offset=offset)


@router.post("/executions/{execution_id}/cancel", response_model=ToolExecutionRead)
async def cancel_execution(request: Request, execution_id: str) -> ToolExecutionRead:
    service: ToolService = request.app.state.tool_service
    return execution_to_read(await service.cancel(execution_id))


@router.get("/confirmations", response_model=list[ToolConfirmationRead])
async def pending_confirmations(request: Request) -> list[ToolConfirmationRead]:
    service: ToolService = request.app.state.tool_service
    return await service.pending_confirmations()


@router.post(
    "/confirmations/{confirmation_id}/approve",
    response_model=ToolConfirmationActionResponse,
)
async def approve_confirmation(
    request: Request, confirmation_id: str
) -> ToolConfirmationActionResponse:
    service: ToolService = request.app.state.tool_service
    execution, confirmation = await service.approve(confirmation_id)
    return ToolConfirmationActionResponse(
        execution=execution_to_read(execution),
        confirmation=confirmation_to_read(confirmation),
    )


@router.post(
    "/confirmations/{confirmation_id}/deny",
    response_model=ToolConfirmationActionResponse,
)
async def deny_confirmation(
    request: Request, confirmation_id: str
) -> ToolConfirmationActionResponse:
    service: ToolService = request.app.state.tool_service
    execution, confirmation = await service.deny(confirmation_id)
    return ToolConfirmationActionResponse(
        execution=execution_to_read(execution),
        confirmation=confirmation_to_read(confirmation),
    )
