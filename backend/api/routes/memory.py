"""Memory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response
from starlette import status

from backend.api.schemas.memory import (
    MemoryCreateRequest,
    MemoryExportResponse,
    MemoryListResponse,
    MemoryPatchRequest,
    MemoryRead,
    MemorySearchRequest,
    MemorySearchResponse,
)
from backend.services.memory import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=120),
    memory_type: str | None = Query(default=None, max_length=40),
    enabled: bool | None = Query(default=None),
) -> MemoryListResponse:
    service: MemoryService = request.app.state.memory_service
    return await service.list_memories(
        limit=limit,
        offset=offset,
        search=search,
        memory_type=memory_type,
        enabled=enabled,
    )


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(request: Request, body: MemoryCreateRequest) -> MemoryRead:
    service: MemoryService = request.app.state.memory_service
    return await service.create(body)


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(request: Request, body: MemorySearchRequest) -> MemorySearchResponse:
    service: MemoryService = request.app.state.memory_service
    return await service.search(body)


@router.post("/export", response_model=MemoryExportResponse)
async def export_memory(request: Request) -> MemoryExportResponse:
    service: MemoryService = request.app.state.memory_service
    return await service.export()


@router.get("/{memory_id}", response_model=MemoryRead)
async def get_memory(request: Request, memory_id: str) -> MemoryRead:
    service: MemoryService = request.app.state.memory_service
    return await service.get(memory_id)


@router.patch("/{memory_id}", response_model=MemoryRead)
async def patch_memory(request: Request, memory_id: str, body: MemoryPatchRequest) -> MemoryRead:
    service: MemoryService = request.app.state.memory_service
    return await service.patch(memory_id, body)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_memory(request: Request, memory_id: str) -> Response:
    service: MemoryService = request.app.state.memory_service
    await service.delete(memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
