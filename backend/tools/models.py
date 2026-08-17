"""Tool framework domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class PermissionClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    WRITE_LOCAL = "WRITE_LOCAL"
    HIGH_IMPACT = "HIGH_IMPACT"
    NETWORK = "NETWORK"


class ToolStatus(StrEnum):
    REQUESTED = "requested"
    PENDING_CONFIRMATION = "pending_confirmation"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class PermissionDecisionType(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


class ToolContext(BaseModel):
    user_id: str
    conversation_id: str | None = None
    agent_id: str | None = None
    request_id: str | None = None
    generation_id: str | None = None
    working_directory: str
    policy_snapshot: dict[str, Any]


class ToolResult(BaseModel):
    execution_id: str
    tool: str
    status: ToolStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    permission_class: PermissionClass
    capabilities: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PermissionDecision(BaseModel):
    decision: PermissionDecisionType
    permission_class: PermissionClass
    reason: str
    risk_level: str
    risk_summary: str


class ToolRequest(BaseModel):
    tool_name: str = Field(min_length=2, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    agent_id: str | None = Field(default=None, max_length=120)
    request_id: str | None = Field(default=None, max_length=120)
    generation_id: str | None = Field(default=None, max_length=80)


class BaseTool(Protocol):
    name: str
    description: str
    permission_class: PermissionClass
    capabilities: list[str]
    input_schema: dict[str, Any]
    enabled: bool

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    def classify(self, validated_input: dict[str, Any]) -> PermissionClass: ...

    async def execute(
        self,
        context: ToolContext,
        validated_input: dict[str, Any],
        *,
        execution_id: str,
    ) -> ToolResult: ...
