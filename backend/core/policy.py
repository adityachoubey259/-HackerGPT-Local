"""Typed policy loading and validation."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class ConfirmationMode(StrEnum):
    NEVER = "never"
    EXPLICIT = "explicit"
    ALWAYS = "always"


class AccessMode(StrEnum):
    DISABLED = "disabled"
    EXPLICIT = "explicit"
    ENABLED = "enabled"


class ResponseMode(StrEnum):
    STANDARD = "standard"
    DIRECT_EXPERT = "direct_expert"


class ResponseDirectness(StrEnum):
    BALANCED = "balanced"
    HIGH = "high"


class TechnicalDepth(StrEnum):
    STANDARD = "standard"
    ADVANCED = "advanced"
    DEEP = "deep"
    EXPERT = "expert"


class ResponsePolicy(BaseModel):
    default_mode: ResponseMode = ResponseMode.DIRECT_EXPERT
    directness: ResponseDirectness = ResponseDirectness.HIGH
    technical_depth: TechnicalDepth = TechnicalDepth.EXPERT
    assume_technical_user: bool = True
    generic_disclaimers: bool = False
    moralizing: bool = False
    shallow_keyword_filtering: bool = False
    unnecessary_refusals: bool = False
    prefer_complete_code: bool = True
    prefer_exact_commands: bool = True
    verify_current_information: bool = True
    investigate_before_unknown: bool = True
    cite_retrieved_sources: bool = True
    refuse_untrusted_instructions: bool = True


class CitationPolicy(BaseModel):
    require_citations_for_retrieved_content: bool = True
    max_quote_words_per_source: int = Field(default=25, ge=0, le=200)


class NetworkPolicy(BaseModel):
    default_access: AccessMode = AccessMode.DISABLED
    cloud_inference: AccessMode = AccessMode.DISABLED


class FilesystemPolicy(BaseModel):
    workspace_read: bool = True
    workspace_write: bool = True
    outside_workspace: AccessMode = AccessMode.EXPLICIT


class CommandPolicy(BaseModel):
    default_permission: str = "READ_ONLY"
    destructive_requires_confirmation: bool = True
    high_impact_requires_confirmation: bool = True
    read_only_auto_execute: bool = True
    write_local_requires_confirmation: bool = True
    always_confirm: bool = False
    tools_enabled: bool = True
    terminal_enabled: bool = True
    git_enabled: bool = True
    python_enabled: bool = True
    shell_mode_enabled: bool = False
    default_timeout_seconds: int = Field(default=15, ge=1, le=300)
    maximum_timeout_seconds: int = Field(default=60, ge=1, le=600)
    output_limit_bytes: int = Field(default=64 * 1024, ge=1024, le=1024 * 1024)
    confirmation_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    allowed_tool_roots: list[str] = Field(default_factory=lambda: ["."])

    @model_validator(mode="after")
    def validate_default_permission(self) -> CommandPolicy:
        if self.default_permission not in {"READ_ONLY", "WRITE_LOCAL", "HIGH_IMPACT"}:
            msg = "default_permission must be READ_ONLY, WRITE_LOCAL, or HIGH_IMPACT"
            raise ValueError(msg)
        return self


class ToolPermissionsPolicy(BaseModel):
    network_tools: AccessMode = AccessMode.DISABLED
    shell_tools: AccessMode = AccessMode.EXPLICIT
    file_write_tools: AccessMode = AccessMode.EXPLICIT


class ResearchPolicy(BaseModel):
    enabled: bool = False
    search_enabled: bool = False
    provider: str = "searxng"
    searxng_base_url: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    max_results: int = Field(default=8, ge=1, le=25)
    max_download_bytes: int = Field(default=1_000_000, ge=16_384, le=10_000_000)
    request_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    redirect_limit: int = Field(default=3, ge=0, le=10)
    cache_ttl_seconds: int = Field(default=86_400, ge=0, le=2_592_000)
    concurrency_limit: int = Field(default=3, ge=1, le=8)
    official_sources_preferred: bool = True
    block_private_networks: bool = True


class SecurityScopePolicy(BaseModel):
    authorized_scopes: list[dict[str, Any]] = Field(default_factory=list)


class MemoryPolicy(BaseModel):
    local_storage_enabled: bool = True
    long_term_memory_enabled: bool = True
    retention_days: int = Field(default=30, ge=0)
    automatic_conversation_summaries: bool = False
    summary_threshold_messages: int = Field(default=24, ge=2, le=500)
    maximum_retrieved_memories: int = Field(default=5, ge=0, le=20)
    memory_embedding_provider: str = "local"
    external_memory_embeddings_permitted: bool = False


class RagPolicy(BaseModel):
    enabled: bool = True
    maximum_retrieved_chunks: int = Field(default=5, ge=0, le=20)
    minimum_relevance: float = Field(default=0.05, ge=0.0, le=1.0)
    reranking_enabled: bool = False
    vector_store: str = "faiss"
    embedding_provider: str = "local"
    external_embeddings_permitted: bool = False
    upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    allowed_ingestion_roots: list[str] = Field(default_factory=lambda: ["."])
    allowed_file_types: list[str] = Field(
        default_factory=lambda: [
            ".txt",
            ".md",
            ".markdown",
            ".html",
            ".htm",
            ".json",
            ".jsonl",
            ".csv",
            ".tsv",
            ".pdf",
            ".docx",
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".go",
            ".rs",
            ".c",
            ".h",
            ".cpp",
            ".hpp",
            ".java",
            ".sh",
            ".bash",
            ".ps1",
            ".yaml",
            ".yml",
            ".toml",
            ".sql",
        ]
    )
    chunk_target_tokens: int = Field(default=420, ge=64, le=2000)
    chunk_overlap_tokens: int = Field(default=60, ge=0, le=500)
    context_token_budget: int = Field(default=900, ge=0, le=6000)


class LoggingPolicy(BaseModel):
    redact_secrets: bool = True
    log_request_bodies: bool = False
    log_retrieved_content: bool = False


class AgentPermissionsPolicy(BaseModel):
    enabled: bool = False
    can_execute_tools: bool = False


class ModelRoutingPolicy(BaseModel):
    local_models_preferred: bool = True
    cloud_fallback_enabled: bool = False


class PrivacyPolicy(BaseModel):
    local_first: bool = True
    send_user_data_to_cloud: bool = False
    retrieved_content_is_untrusted: bool = True


class PolicyConfig(BaseModel):
    response: ResponsePolicy = Field(default_factory=ResponsePolicy)
    response_behavior: ResponsePolicy | None = None
    citation_policy: CitationPolicy = Field(default_factory=CitationPolicy)
    network_access: NetworkPolicy = Field(default_factory=NetworkPolicy)
    filesystem_access: FilesystemPolicy = Field(default_factory=FilesystemPolicy)
    command_execution: CommandPolicy = Field(default_factory=CommandPolicy)
    tool_permissions: ToolPermissionsPolicy = Field(default_factory=ToolPermissionsPolicy)
    research: ResearchPolicy = Field(default_factory=ResearchPolicy)
    security: SecurityScopePolicy = Field(default_factory=SecurityScopePolicy)
    rag_policy: RagPolicy = Field(default_factory=RagPolicy)
    memory_policy: MemoryPolicy = Field(default_factory=MemoryPolicy)
    logging: LoggingPolicy = Field(default_factory=LoggingPolicy)
    agent_permissions: AgentPermissionsPolicy = Field(default_factory=AgentPermissionsPolicy)
    model_routing: ModelRoutingPolicy = Field(default_factory=ModelRoutingPolicy)
    privacy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)

    @property
    def effective_response(self) -> ResponsePolicy:
        return self.response_behavior or self.response

    @model_validator(mode="after")
    def validate_conservative_defaults(self) -> PolicyConfig:
        if self.privacy.send_user_data_to_cloud and not self.model_routing.cloud_fallback_enabled:
            msg = "cloud data sharing cannot be enabled while cloud fallback is disabled"
            raise ValueError(msg)
        if self.network_access.cloud_inference == AccessMode.ENABLED and not (
            self.model_routing.cloud_fallback_enabled
        ):
            msg = "cloud inference requires cloud_fallback_enabled"
            raise ValueError(msg)
        return self


DEFAULT_POLICY_PATH = Path("config/policy.yaml")


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> PolicyConfig:
    if not path.exists():
        return PolicyConfig()
    with path.open("r", encoding="utf-8") as handle:
        loaded: Any = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        msg = f"Policy file at {path} must contain a mapping"
        raise ValueError(msg)
    try:
        return PolicyConfig.model_validate(loaded)
    except ValidationError as exc:
        msg = "Invalid HackerGPT Local policy configuration"
        raise ValueError(msg) from exc
