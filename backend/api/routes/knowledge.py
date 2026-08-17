"""Knowledge ingestion and RAG endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from starlette import status

from backend.api.schemas.knowledge import (
    DocumentDetailResponse,
    IngestionJobRead,
    IngestPathRequest,
    KnowledgeListResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
)
from backend.services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgeListResponse)
async def list_documents(
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
) -> KnowledgeListResponse:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.list_documents(
        limit=limit, offset=offset, search=search, status=status_filter
    )


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats(request: Request) -> KnowledgeStatsResponse:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.stats()


@router.post("/upload", response_model=IngestionJobRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    tags: Annotated[str, Form()] = "",
) -> IngestionJobRead:
    service: KnowledgeService = request.app.state.knowledge_service
    content = await file.read()
    tag_values = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return await service.ingest_upload(
        filename=file.filename or "document",
        content=content,
        mime_type=file.content_type,
        tags=tag_values,
    )


@router.post("/ingest-path", response_model=list[IngestionJobRead])
async def ingest_path(request: Request, body: IngestPathRequest) -> list[IngestionJobRead]:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.ingest_path(body.path, tags=body.tags)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: Request,
    body: KnowledgeSearchRequest,
) -> KnowledgeSearchResponse:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.search(body)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def document_detail(request: Request, document_id: str) -> DocumentDetailResponse:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.detail(document_id)


@router.post("/{document_id}/reindex", response_model=IngestionJobRead)
async def reindex_document(request: Request, document_id: str) -> IngestionJobRead:
    service: KnowledgeService = request.app.state.knowledge_service
    return await service.reindex(document_id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_document(request: Request, document_id: str) -> Response:
    service: KnowledgeService = request.app.state.knowledge_service
    await service.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
