"""System information endpoints."""

from fastapi import APIRouter, Request

from backend.api.schemas.hardware import HardwareReport
from backend.api.schemas.system import KnowledgeMemoryStatusResponse, SystemInfoResponse
from backend.services.health import HealthService
from backend.system.hardware import cached_hardware_report

router = APIRouter(tags=["system"])


@router.get("/system/info", response_model=SystemInfoResponse)
async def system_info(request: Request) -> SystemInfoResponse:
    service: HealthService = request.app.state.health_service
    return service.system_info()


@router.get("/system/hardware", response_model=HardwareReport)
async def system_hardware() -> HardwareReport:
    return cached_hardware_report()


@router.get("/system/knowledge-memory", response_model=KnowledgeMemoryStatusResponse)
async def knowledge_memory_status(request: Request) -> KnowledgeMemoryStatusResponse:
    knowledge = await request.app.state.knowledge_service.stats()
    memory = await request.app.state.memory_service.stats()
    return KnowledgeMemoryStatusResponse(
        rag=knowledge.model_dump(),
        memory=memory,
    )
