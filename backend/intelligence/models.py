"""Typed model routing and context-engine domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from backend.llm.domain import LLMMessage, NormalizedModel, ProviderHealth
from backend.system.hardware import HardwareReport


class TaskCategory(StrEnum):
    GENERAL = "general"
    REASONING = "reasoning"
    CODING = "coding"
    DEBUGGING = "debugging"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    API_DESIGN = "api_design"
    SDK_DEVELOPMENT = "sdk_development"
    SYSTEM_DESIGN = "system_design"
    DEVOPS = "devops"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENT = "document"
    RESEARCH = "research"
    CYBERSECURITY = "cybersecurity"
    REVERSE_ENGINEERING = "reverse_engineering"
    MALWARE_ANALYSIS = "malware_analysis"
    PROMPT_ENGINEERING = "prompt_engineering"
    LONG_CONTEXT = "long_context"
    TOOL_USE = "tool_use"


class RouterMode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"
    LOCAL_ONLY = "local_only"
    QUALITY_FIRST = "quality_first"
    SPEED_FIRST = "speed_first"
    LOW_MEMORY = "low_memory"


class HardwareFit(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    POSSIBLE_SLOWER = "possible/slower"
    CPU_HEAVY = "cpu-heavy"
    NOT_RECOMMENDED = "not recommended"
    UNKNOWN = "unknown"


class ContextSource(StrEnum):
    SYSTEM = "system"
    AGENT = "agent"
    USER = "user"
    CONVERSATION = "conversation"
    MEMORY = "memory"
    PROJECT = "project"
    RAG = "rag"
    WEB = "web"
    TOOL = "tool"


class ModelCapabilityProfile(BaseModel):
    pattern: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    context_length: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    coding_score: float = Field(default=0.5, ge=0, le=1)
    reasoning_score: float = Field(default=0.5, ge=0, le=1)
    speed_score: float = Field(default=0.5, ge=0, le=1)
    tool_support: bool | None = None
    vision: bool | None = None
    structured_output: bool | None = None
    recommended_agents: list[str] = Field(default_factory=list)
    estimated_vram_bytes: int | None = Field(default=None, ge=1)
    estimated_ram_bytes: int | None = Field(default=None, ge=1)
    default_generation: dict[str, Any] = Field(default_factory=dict)


class RoutingRequest(BaseModel):
    message: str = Field(default="", max_length=12000)
    explicit_task: TaskCategory | None = None
    mode: RouterMode = RouterMode.AUTO
    manual_provider: str | None = None
    manual_model: str | None = None
    agent_id: str | None = None
    requires_tools: bool = False
    requires_vision: bool = False
    min_context_tokens: int | None = Field(default=None, ge=1)
    latency_preference: str | None = None


class ModelCandidate(BaseModel):
    provider: str
    model: str
    display_name: str
    score: float
    hardware_fit: HardwareFit
    local: bool
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    provider: str | None
    model: str | None
    mode: RouterMode
    task: TaskCategory
    manual: bool
    candidates: list[ModelCandidate]
    diagnostics: list[str]
    error: str | None = None


class RoutingSnapshot(BaseModel):
    providers: list[ProviderHealth]
    models: list[NormalizedModel]
    hardware: HardwareReport


class ContextBudget(BaseModel):
    context_limit: int
    reserved_output_tokens: int
    safety_margin_tokens: int
    available_input_tokens: int
    estimated_input_tokens: int = 0
    trimmed_tokens: int = 0
    estimated: bool = True


class ContextItem(BaseModel):
    source: ContextSource
    role: str
    content: str
    priority: int
    estimated_tokens: int
    citation_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreparedContext(BaseModel):
    messages: list[LLMMessage]
    items: list[ContextItem]
    budget: ContextBudget
    diagnostics: dict[str, Any]
