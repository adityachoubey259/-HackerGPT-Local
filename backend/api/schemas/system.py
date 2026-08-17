"""System response schemas."""

from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    application_version: str
    environment: str
    python_version: str
    operating_system: str
    architecture: str
    hostname: str | None
    database_type: str
    debug: bool
    uptime_seconds: float


class PublicConfigResponse(BaseModel):
    environment: str
    debug: bool
    network_access: bool
    api: dict[str, object]
    model_endpoint: dict[str, object]
    response: dict[str, object]


class KnowledgeMemoryStatusResponse(BaseModel):
    rag: dict[str, object]
    memory: dict[str, object]
