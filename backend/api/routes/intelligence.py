"""Advanced intelligence engine endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.intelligence.models import (
    ModelCapabilityProfile,
    RoutingDecision,
    RoutingRequest,
)
from backend.services.intelligence import IntelligenceService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/route", response_model=RoutingDecision)
async def route_model(request: Request, body: RoutingRequest) -> RoutingDecision:
    service: IntelligenceService = request.app.state.intelligence_service
    return await service.route(body)


@router.get("/model-profiles", response_model=list[ModelCapabilityProfile])
async def model_profiles(request: Request) -> list[ModelCapabilityProfile]:
    service: IntelligenceService = request.app.state.intelligence_service
    return service.profiles.list()
