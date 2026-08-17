"""Conversation and chat API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.llm.domain import GenerationSettings, GenerationStatus, TokenUsage


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Pagination(BaseModel):
    limit: int = Field(default=30, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    total: int


class MessageRead(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_request_id: str | None = None
    generation_id: str | None = None
    generation_status: GenerationStatus | None = None
    provider: str | None = None
    model: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    time_to_first_token_ms: float | None = None
    duration_ms: float | None = None
    tokens_per_second: float | None = None
    created_at: datetime
    updated_at: datetime


class ConversationRead(BaseModel):
    id: str
    user_id: str
    title: str
    agent_id: str | None = None
    archived: bool
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]
    pagination: Pagination


class MessageListResponse(BaseModel):
    items: list[MessageRead]
    pagination: Pagination


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = " ".join(value.split())
        return candidate or None


class ConversationPatchRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    archived: bool | None = None
    agent_id: str | None = Field(default=None, max_length=120)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = " ".join(value.split())
        if not candidate:
            msg = "title cannot be empty"
            raise ValueError(msg)
        return candidate


class ChatStreamRequest(BaseModel):
    conversation_id: str | None = None
    client_request_id: str = Field(min_length=8, max_length=120)
    message: str = Field(min_length=1, max_length=16000)
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=240)
    agent_id: str | None = Field(default=None, max_length=120)
    settings: GenerationSettings = Field(default_factory=GenerationSettings)

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            msg = "message cannot be empty"
            raise ValueError(msg)
        return candidate

    @field_validator("provider", "model", "client_request_id", "agent_id")
    @classmethod
    def trim_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        if not candidate:
            msg = "identifier cannot be empty"
            raise ValueError(msg)
        return candidate


class StreamMeta(BaseModel):
    request_id: str
    generation_id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    provider: str
    model: str
    agent_id: str | None = None
    created_at: datetime


class StreamUsage(TokenUsage):
    estimated: bool = False


class StreamMetrics(BaseModel):
    time_to_first_token_ms: float | None = None
    duration_ms: float | None = None
    tokens_per_second: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class StreamError(BaseModel):
    code: str
    message: str
    request_id: str
    generation_id: str | None = None
    retryable: bool = False


class StreamDone(BaseModel):
    assistant_message_id: str
    status: GenerationStatus
    finish_reason: str | None = None
