"""Health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.core import get_db_session
from backend.api.schemas.health import HealthResponse, ReadinessResponse
from backend.services.health import HealthService

router = APIRouter(tags=["health"])
DbSessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(
    request: Request,
    session: DbSessionDependency,
) -> ReadinessResponse:
    service: HealthService = request.app.state.health_service
    return await service.readiness(session)
