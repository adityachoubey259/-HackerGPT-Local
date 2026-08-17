"""Local observability and diagnostic export endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.services.observability import ObservabilityService

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/metrics", response_model=dict[str, Any])
async def local_metrics(request: Request) -> dict[str, Any]:
    service: ObservabilityService = request.app.state.observability_service
    return service.metrics()


@router.get("/export", response_model=dict[str, Any])
async def diagnostic_export(request: Request) -> dict[str, Any]:
    service: ObservabilityService = request.app.state.observability_service
    return service.diagnostic_export()
