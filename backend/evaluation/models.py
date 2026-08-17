"""Versioned evaluation domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCategory(StrEnum):
    CODING = "coding"
    DEBUGGING = "debugging"
    PROMPT_GENERATION = "prompt_generation"
    RAG = "rag"
    RESEARCH = "research"
    SECURITY_LAB = "security_lab"
    GENERAL = "general"


class EvaluationDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationCase(BaseModel):
    id: str
    category: EvaluationCategory = EvaluationCategory.GENERAL
    prompt: str = Field(min_length=1)
    expected_characteristics: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    rubric: list[str] = Field(default_factory=list)
    required_citations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: EvaluationDifficulty = EvaluationDifficulty.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationDataset(BaseModel):
    id: str
    version: str = "1"
    description: str
    cases: list[EvaluationCase]
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunRequest(BaseModel):
    dataset_id: str
    candidate_name: str = "candidate"
    answers: dict[str, str] = Field(default_factory=dict)
    compare_to: str | None = None


class EvaluationCaseResult(BaseModel):
    case_id: str
    category: EvaluationCategory
    score: float = Field(ge=0, le=1)
    passed: bool
    missing_characteristics: list[str] = Field(default_factory=list)
    citation_failures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    total_cases: int
    passed_cases: int
    mean_score: float
    by_category: dict[str, dict[str, float | int]]


class EvaluationRun(BaseModel):
    id: str
    dataset_id: str
    dataset_version: str
    candidate_name: str
    results: list[EvaluationCaseResult]
    summary: EvaluationSummary
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
