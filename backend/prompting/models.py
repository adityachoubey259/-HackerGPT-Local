"""Prompt Architect typed models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PromptLevel(StrEnum):
    QUICK = "quick"
    PROFESSIONAL = "professional"
    ADVANCED = "advanced"
    EXPERT = "expert"
    PRINCIPAL_RESEARCH = "principal_research"


class PromptType(StrEnum):
    CODING = "coding"
    DEBUGGING = "debugging"
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULL_STACK = "full_stack"
    API = "api"
    SDK = "sdk"
    DATABASE = "database"
    DEVOPS = "devops"
    SYSTEM_DESIGN = "system_design"
    ARCHITECTURE = "architecture"
    REFACTORING = "refactoring"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY_REVIEW = "security_review"
    ETHICAL_HACKING_LAB = "ethical_hacking_lab"
    CYBERSECURITY_LAB = "cybersecurity_lab"
    REVERSE_ENGINEERING = "reverse_engineering"
    MALWARE_ANALYSIS = "malware_analysis"
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    AI_ML = "ai_ml"
    RAG = "rag"
    AGENTS = "agents"
    PROMPT_ENGINEERING = "prompt_engineering"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    MIGRATION = "migration"


class PromptProfile(BaseModel):
    id: str
    label: str
    prompt_type: PromptType
    domains: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    default_agent: str | None = None
    recommended_capabilities: list[str] = Field(default_factory=list)
    required_context_sources: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)


class PromptArchitectRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=8000)
    prompt_type: PromptType = PromptType.CODING
    level: PromptLevel = PromptLevel.ADVANCED
    domain: str | None = None
    language: str | None = None
    framework: str | None = None
    target_agent: str | None = None
    target_model: str | None = None
    output_format: str | None = None
    constraints: list[str] = Field(default_factory=list, max_length=20)
    available_tools: list[str] = Field(default_factory=list, max_length=50)
    use_rag: bool = True
    use_memory: bool = True
    use_live_research: bool = False
    testing_required: bool = True
    security_required: bool = True


class PromptArchitectResponse(BaseModel):
    optimized_prompt: str
    system_prompt: str | None
    structured_output_schema: dict[str, Any] | None
    recommended_agent: str | None
    recommended_model_capability: str | None
    recommended_context_sources: list[str]
    assumptions: list[str]
    profile: PromptProfile | None
