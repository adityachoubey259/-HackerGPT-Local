"""Live web research endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.api.schemas.research import (
    ResearchHistoryResponse,
    ResearchRetrieveRequest,
    ResearchRunRequest,
    ResearchRunResponse,
    ResearchStatusResponse,
    RetrievedPageResponse,
)
from backend.services.research import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/status", response_model=ResearchStatusResponse)
async def research_status(request: Request) -> ResearchStatusResponse:
    service: ResearchService = request.app.state.research_service
    return service.status()


@router.get("/history", response_model=ResearchHistoryResponse)
async def research_history(
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ResearchHistoryResponse:
    service: ResearchService = request.app.state.research_service
    return await service.history(limit=limit, offset=offset)


@router.post("/run", response_model=ResearchRunResponse)
async def run_research(request: Request, body: ResearchRunRequest) -> ResearchRunResponse:
    service: ResearchService = request.app.state.research_service
    return await service.run(body)


@router.post("/retrieve", response_model=RetrievedPageResponse)
async def retrieve_source(request: Request, body: ResearchRetrieveRequest) -> RetrievedPageResponse:
    service: ResearchService = request.app.state.research_service
    return await service.retrieve(body)
