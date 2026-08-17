"""Training backend, preflight, dataset, and artifact models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TrainingFit(StrEnum):
    RECOMMENDED = "recommended"
    POSSIBLE = "possible"
    SLOW = "slow"
    UNLIKELY_TO_FIT = "unlikely_to_fit"
    UNSUPPORTED = "unsupported"


class TrainingPreset(StrEnum):
    QUICK = "quick"
    BALANCED = "balanced"
    QUALITY = "quality"
    CUSTOM = "custom"


class TrainingState(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    LOADING_MODEL = "loading_model"
    TRAINING = "training"
    VALIDATING = "validating"
    SAVING = "saving"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    REQUIRES_BACKEND = "requires_backend"


class TrainingBackendCapabilities(BaseModel):
    backend_id: str
    label: str
    supported_model_families: list[str] = Field(default_factory=list)
    adapter_types: list[str] = Field(default_factory=list)
    quantized_training_available: bool
    gpu_required: bool
    cpu_compatible: bool
    checkpoint_support: bool
    resume_support: bool
    cancellation_support: bool
    installed: bool
    install_hint: str | None = None


class TrainingPresetConfig(BaseModel):
    preset: TrainingPreset
    epochs: float
    max_steps: int
    learning_rate: float
    batch_size: int
    gradient_accumulation_steps: int
    sequence_length: int
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    validation_split: float


class TrainingPreflightRequest(BaseModel):
    dataset_version_id: str
    base_model: str
    backend_id: str = "transformers-peft"
    adapter_type: str = "lora"
    preset: TrainingPreset = TrainingPreset.QUICK
    sequence_length: int = Field(default=256, ge=32, le=8192)
    quantized: bool = False


class TrainingPreflightResult(BaseModel):
    backend: TrainingBackendCapabilities
    fit: TrainingFit
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)
    hardware: dict[str, Any]
    dataset: dict[str, Any]
    preset: TrainingPresetConfig


class TrainingDatasetExport(BaseModel):
    dataset_version_id: str
    export_path: str
    example_count: int
    train_count: int
    validation_count: int
    test_count: int
    duplicate_count: int
    min_tokens: int
    max_tokens: int
    median_tokens: int
    p95_tokens: int
    total_estimated_tokens: int
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TrainingProgress(BaseModel):
    state: TrainingState
    progress: float = Field(default=0, ge=0, le=1)
    epoch: float | None = None
    step: int = 0
    total_steps: int | None = None
    training_loss: float | None = None
    validation_loss: float | None = None
    learning_rate: float | None = None
    elapsed_seconds: float = 0
    accelerator: str = "unknown"
    memory: dict[str, Any] = Field(default_factory=dict)
    checkpoint_path: str | None = None
    artifact_id: str | None = None
    artifact_path: str | None = None
    resumable: bool = False
    logs: list[str] = Field(default_factory=list)
    error: str | None = None


class TrainingWorkerRequest(BaseModel):
    job_id: str
    dataset_version_id: str
    dataset_path: str
    output_dir: str
    base_model: str
    backend_id: str
    adapter_type: str
    preset: TrainingPresetConfig
    quantized: bool = False
    resume_from_checkpoint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingArtifactManifest(BaseModel):
    artifact_id: str
    job_id: str
    base_model: str
    adapter_type: str
    backend_id: str
    artifact_path: str
    dataset_version_id: str
    checksums: dict[str, str]
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactEvaluationRequest(BaseModel):
    evaluation_dataset_id: str = "v1-core"
    base_candidate_name: str = "base"
    adapter_candidate_name: str = "adapter"


class ArtifactEvaluationComparison(BaseModel):
    artifact_id: str
    evaluation_dataset_id: str
    base_run_id: str
    adapter_run_id: str
    by_category: dict[str, str]
    promoted_allowed: bool
    blocking_regressions: list[str] = Field(default_factory=list)
