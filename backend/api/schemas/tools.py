"""Tool API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.tools.models import PermissionClass, ToolDefinition, ToolStatus


class ToolListResponse(BaseModel):
    items: list[ToolDefinition]


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(min_length=2, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    agent_id: str | None = Field(default=None, max_length=120)


class ToolExecutionRead(BaseModel):
    id: str
    tool_name: str
    permission_class: PermissionClass
    status: ToolStatus
    input: dict[str, Any]
    working_directory: str | None
    command_display: str | None
    stdout: str | None
    stderr: str | None
    exit_code: int | None
    data: dict[str, Any]
    error_code: str | None
    error_message: str | None
    truncated: bool
    duration_ms: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ToolExecutionListResponse(BaseModel):
    items: list[ToolExecutionRead]
    total: int


class ToolConfirmationRead(BaseModel):
    id: str
    execution_id: str
    tool_name: str
    permission_class: PermissionClass
    status: str
    risk_summary: str
    expires_at: datetime
    created_at: datetime


class ToolExecuteResponse(BaseModel):
    execution: ToolExecutionRead
    confirmation: ToolConfirmationRead | None = None
    decision: str
    reason: str


class ToolConfirmationActionResponse(BaseModel):
    execution: ToolExecutionRead
    confirmation: ToolConfirmationRead
