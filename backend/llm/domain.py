"""Normalized model provider domain types."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderType(StrEnum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    OPENAI_COMPATIBLE = "openai_compatible"
    VLLM = "vllm"


class ProviderCapability(StrEnum):
    CHAT = "chat"
    COMPLETION = "completion"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    TOOL_CALLING = "tool_calling"
    MODEL_DISCOVERY = "model_discovery"


class ProviderHealthStatus(StrEnum):
    CONFIGURED = "configured"
    DISABLED = "disabled"
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    MISCONFIGURED = "misconfigured"


class ModelFit(StrEnum):
    EXCELLENT = "excellent"
    SUITABLE = "suitable"
    CONSTRAINED = "constrained"
    CPU_PARTIAL_OFFLOAD = "cpu/partial-offload"
    NOT_RECOMMENDED = "not recommended"
    UNKNOWN = "unknown"


class LLMMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ReasoningMode(StrEnum):
    AUTO = "auto"
    FAST = "fast"
    DEEP = "deep"


class LLMStreamEventType(StrEnum):
    DELTA = "delta"
    USAGE = "usage"
    METRICS = "metrics"
    ERROR = "error"
    DONE = "done"


class LLMMessage(BaseModel):
    role: LLMMessageRole
    content: str


class GenerationSettings(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=128, ge=1, le=4096)
    reasoning_mode: ReasoningMode = ReasoningMode.AUTO
    seed: int | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ModelCallMetrics(BaseModel):
    provider: str
    model: str
    duration_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    tokens_per_second: float | None = None
    success: bool


class LLMStreamEvent(BaseModel):
    type: LLMStreamEventType
    text: str | None = None
    usage: TokenUsage | None = None
    metrics: ModelCallMetrics | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    finish_reason: str | None = None


class ProviderHealth(BaseModel):
    provider: str
    type: ProviderType
    status: ProviderHealthStatus
    message: str | None = None
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    base_url: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class NormalizedModel(BaseModel):
    id: str
    name: str
    provider: str
    provider_model_id: str
    family: str | None = None
    architecture: str | None = None
    parameter_count: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    size_bytes: int | None = None
    estimated_ram_bytes: int | None = None
    estimated_vram_bytes: int | None = None
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    modified_at: datetime | None = None
    loaded: bool | None = None
    suitability: ModelFit | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelTestRequest(BaseModel):
    provider: str
    model: str
    prompt: str = Field(min_length=1, max_length=2000)
    settings: GenerationSettings = Field(default_factory=GenerationSettings)

    @field_validator("provider", "model")
    @classmethod
    def non_empty_identifier(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            msg = "identifier cannot be empty"
            raise ValueError(msg)
        return candidate


class ModelTestResponse(BaseModel):
    provider: str
    model: str
    text: str
    duration_ms: float
    usage: TokenUsage | None = None
    metrics: ModelCallMetrics


class ModelOverride(BaseModel):
    friendly_name: str | None = None
    family: str | None = None
    architecture: str | None = None
    parameter_count: str | None = None
    quantization: str | None = None
    context_length: int | None = Field(default=None, ge=1)
    estimated_ram_bytes: int | None = Field(default=None, ge=1)
    estimated_vram_bytes: int | None = Field(default=None, ge=1)
    preferred_usage: str | None = None
    enabled: bool = True


class ProviderConfig(BaseModel):
    enabled: bool = True
    type: ProviderType
    base_url: str
    label: str | None = None
    api_key: str | None = Field(default=None, exclude=True)
    health_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    list_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    metadata_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    generation_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    reasoning_enabled: bool = False
    model_overrides: dict[str, ModelOverride] = Field(default_factory=dict)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        candidate = value.rstrip("/")
        if not candidate.startswith(("http://", "https://")):
            msg = "provider base_url must be http or https"
            raise ValueError(msg)
        return candidate


class ModelProviderConfiguration(BaseModel):
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    default_provider: str | None = None
    default_model: str | None = None

    @model_validator(mode="after")
    def validate_defaults(self) -> ModelProviderConfiguration:
        if self.default_provider is not None and self.default_provider not in self.providers:
            msg = "default_provider must reference a configured provider"
            raise ValueError(msg)
        return self
