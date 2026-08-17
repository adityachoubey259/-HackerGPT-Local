"""Advanced cybersecurity workspace endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.api.schemas.security import (
    SecurityDashboardResponse,
    SecurityExportResponse,
    SecurityFindingCreate,
    SecurityFindingListResponse,
    SecurityFindingRead,
    SecurityNoteCreate,
    SecurityNoteListResponse,
    SecurityNoteRead,
    SecurityScopeCreate,
    SecurityScopeListResponse,
    SecurityScopeRead,
    SecurityWorkspaceCreate,
    SecurityWorkspaceListResponse,
    SecurityWorkspaceRead,
    StaticReviewRequest,
    StaticReviewResponse,
    StaticSampleRequest,
    StaticSampleResponse,
)
from backend.services.security_workspace import SecurityWorkspaceService

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def dashboard(request: Request) -> SecurityDashboardResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.dashboard()


@router.get("/workspaces", response_model=SecurityWorkspaceListResponse)
async def list_workspaces(request: Request) -> SecurityWorkspaceListResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.list_workspaces()


@router.post("/workspaces", response_model=SecurityWorkspaceRead, status_code=201)
async def create_workspace(
    request: Request,
    body: SecurityWorkspaceCreate,
) -> SecurityWorkspaceRead:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.create_workspace(body)


@router.get("/scopes", response_model=SecurityScopeListResponse)
async def list_scopes(
    request: Request,
    workspace_id: str | None = Query(default=None),
) -> SecurityScopeListResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.list_scopes(workspace_id=workspace_id)


@router.post("/scopes", response_model=SecurityScopeRead, status_code=201)
async def create_scope(request: Request, body: SecurityScopeCreate) -> SecurityScopeRead:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.create_scope(body)


@router.get("/findings", response_model=SecurityFindingListResponse)
async def list_findings(
    request: Request,
    workspace_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SecurityFindingListResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.list_findings(
        workspace_id=workspace_id,
        severity=severity,
        limit=limit,
        offset=offset,
    )


@router.post("/findings", response_model=SecurityFindingRead, status_code=201)
async def create_finding(request: Request, body: SecurityFindingCreate) -> SecurityFindingRead:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.create_finding(body)


@router.get("/notes", response_model=SecurityNoteListResponse)
async def list_notes(
    request: Request,
    workspace_id: str | None = Query(default=None),
) -> SecurityNoteListResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.list_notes(workspace_id=workspace_id)


@router.post("/notes", response_model=SecurityNoteRead, status_code=201)
async def create_note(request: Request, body: SecurityNoteCreate) -> SecurityNoteRead:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.create_note(body)


@router.post("/static-review", response_model=StaticReviewResponse)
async def static_review(request: Request, body: StaticReviewRequest) -> StaticReviewResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.static_review(body)


@router.post("/samples/inspect", response_model=StaticSampleResponse)
async def inspect_sample(request: Request, body: StaticSampleRequest) -> StaticSampleResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.inspect_sample(body)


@router.get("/workspaces/{workspace_id}/export", response_model=SecurityExportResponse)
async def export_workspace(
    request: Request,
    workspace_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
) -> SecurityExportResponse:
    service: SecurityWorkspaceService = request.app.state.security_workspace_service
    return await service.export_workspace(workspace_id, format)
