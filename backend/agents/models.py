"""Typed agent domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ContextStrategy(StrEnum):
    BALANCED = "balanced"
    CONVERSATION_HEAVY = "conversation-heavy"
    KNOWLEDGE_HEAVY = "knowledge-heavy"
    CODE_FOCUSED = "code-focused"
    CONCISE = "concise"
    DIAGNOSTIC = "diagnostic"


class AgentMemoryConfig(BaseModel):
    enabled: bool = True
    memory_types: list[str] = Field(default_factory=lambda: ["user", "project"])
    maximum_memories: int = Field(default=5, ge=0, le=20)
    project_memory: bool = True
    conversation_summaries: bool = False


class AgentRagConfig(BaseModel):
    enabled: bool = True
    knowledge_scope: str = "all"
    result_limit: int = Field(default=5, ge=0, le=20)
    reranking: bool = False
    source_diversity: bool = True


class AgentToolExecutionConfig(BaseModel):
    enabled: bool = True
    max_tool_calls: int = Field(default=3, ge=0, le=12)
    require_confirmation_for_write: bool = True
    require_confirmation_for_high_impact: bool = True


class AgentDefinition(BaseModel):
    id: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    icon: str = Field(default="sparkles", max_length=80)
    system_prompt: str = Field(min_length=1, max_length=8000)
    preferred_provider: str | None = Field(default=None, max_length=80)
    preferred_model: str | None = Field(default=None, max_length=240)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=512, ge=1, le=32000)
    allowed_tools: list[str] = Field(default_factory=list)
    memory_config: AgentMemoryConfig = Field(default_factory=AgentMemoryConfig)
    rag_config: AgentRagConfig = Field(default_factory=AgentRagConfig)
    context_strategy: ContextStrategy = ContextStrategy.BALANCED
    required_model_capabilities: list[str] = Field(default_factory=list)
    tool_execution_config: AgentToolExecutionConfig = Field(
        default_factory=AgentToolExecutionConfig
    )
    enabled: bool = True
    built_in: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("allowed_tools", "required_model_capabilities")
    @classmethod
    def normalize_identifiers(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_model_preference(self) -> AgentDefinition:
        if self.preferred_model and not self.preferred_provider:
            msg = "preferred_model requires preferred_provider"
            raise ValueError(msg)
        return self

    @property
    def tool_count(self) -> int:
        return len(self.allowed_tools)


class AgentList(BaseModel):
    items: list[AgentDefinition]


class AgentCreate(BaseModel):
    id: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(min_length=1, max_length=8000)
    configuration: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AgentPatch(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    system_prompt: str | None = Field(default=None, max_length=8000)
    configuration: dict[str, Any] | None = None
    enabled: bool | None = None
