"""Health response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class DependencyStatus(BaseModel):
    status: str
    details: dict[str, str] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    status: str
    dependencies: dict[str, DependencyStatus]
