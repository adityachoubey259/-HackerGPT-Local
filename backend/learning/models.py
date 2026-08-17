"""Learning Studio domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LearningSourceType(StrEnum):
    MANUAL = "manual"
    CHAT = "chat"
    CORRECTION = "correction"
    FILE = "file"
    FOLDER = "folder"
    REPOSITORY = "repository"
    RESEARCH = "research"
    API = "api"
    DATABASE = "database"


class DatasetSplit(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class TrainingJobStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    LOADING_MODEL = "loading_model"
    RUNNING = "running"
    TRAINING = "training"
    VALIDATING = "validating"
    SAVING = "saving"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    REQUIRES_BACKEND = "requires_backend"


class ArtifactStatus(StrEnum):
    REGISTERED = "registered"
    DRAFT = "draft"
    VALIDATED = "validated"
    EVALUATED = "evaluated"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    ROLLED_BACK = "rolled_back"
    DELETED = "deleted"


class LearningExample(BaseModel):
    id: str
    source_type: LearningSourceType
    prompt: str
    response: str
    correction: str | None = None
    tags: list[str] = Field(default_factory=list)
    split: DatasetSplit = DatasetSplit.TRAIN
    provenance: dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: str


class LearningExampleCreate(BaseModel):
    source_type: LearningSourceType = LearningSourceType.MANUAL
    prompt: str = Field(min_length=1, max_length=12000)
    response: str = Field(min_length=1, max_length=12000)
    correction: str | None = Field(default=None, max_length=12000)
    tags: list[str] = Field(default_factory=list, max_length=30)
    split: DatasetSplit = DatasetSplit.TRAIN
    provenance: dict[str, Any] = Field(default_factory=dict)


class DatasetVersion(BaseModel):
    id: str
    dataset_id: str
    version: int
    example_ids: list[str]
    train_count: int
    validation_count: int
    test_count: int
    validation_errors: list[str] = Field(default_factory=list)
    checksum: str
    created_at: str


class DatasetVersionCreate(BaseModel):
    dataset_id: str = Field(default="default", min_length=1, max_length=120)
    example_ids: list[str] = Field(default_factory=list)


class TrainingJob(BaseModel):
    id: str
    dataset_version_id: str
    base_model: str
    adapter_type: str = "lora"
    status: TrainingJobStatus
    backend_id: str = "transformers-peft"
    preset: str = "quick"
    progress: float = Field(default=0, ge=0, le=1)
    loss: float | None = None
    step: int = 0
    total_steps: int | None = None
    epoch: float | None = None
    validation_loss: float | None = None
    learning_rate: float | None = None
    elapsed_seconds: float = 0
    accelerator: str = "unknown"
    hardware_fit: str = "unknown"
    logs: list[str] = Field(default_factory=list)
    artifact_id: str | None = None
    checkpoint_path: str | None = None
    artifact_path: str | None = None
    resumable: bool = False
    pid: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class TrainingJobCreate(BaseModel):
    dataset_version_id: str
    base_model: str = Field(min_length=1, max_length=200)
    backend_id: str = Field(default="transformers-peft", min_length=1, max_length=120)
    adapter_type: str = "lora"
    preset: str = "quick"
    sequence_length: int = Field(default=128, ge=32, le=8192)
    quantized: bool = False
    allow_metadata_only: bool = True
    launch_worker: bool = False


class ModelArtifact(BaseModel):
    id: str
    name: str
    base_model: str
    adapter_type: str
    dataset_version_id: str | None = None
    evaluation_run_id: str | None = None
    status: ArtifactStatus = ArtifactStatus.DRAFT
    active: bool = False
    promoted_at: str | None = None
    disk_size_bytes: int | None = None
    checksums: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ArtifactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    base_model: str = Field(min_length=1, max_length=200)
    adapter_type: str = "lora"
    dataset_version_id: str | None = None
    evaluation_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScheduleDefinition(BaseModel):
    id: str
    name: str
    enabled: bool = False
    cadence: str = "manual"
    action: str = "dataset_validation"
    created_at: str


class LearningOverview(BaseModel):
    example_count: int
    dataset_version_count: int
    training_job_count: int
    artifact_count: int
    active_job_count: int
    promoted_artifacts: int
    storage_bytes: int
    recent_evaluation_runs: int
    policy: dict[str, Any]


class DatasetBlueprintExample(BaseModel):
    system: str
    user: str
    assistant: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    split: DatasetSplit = DatasetSplit.TRAIN


class DatasetBlueprint(BaseModel):
    id: str
    version: str
    title: str
    description: str
    format: str
    example_path: str
    recommended_workflow: list[str]
    categories: list[str]
    tags: list[str]
    security_notes: list[str]
    example_count: int
    examples: list[DatasetBlueprintExample]


class SeedDatasetImportResult(BaseModel):
    blueprint_id: str
    imported_count: int
    example_count: int
    dataset: DatasetVersion
