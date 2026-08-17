"""Local-first learning, dataset, training, and artifact registry service."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.learning.models import (
    ArtifactCreate,
    ArtifactStatus,
    DatasetBlueprint,
    DatasetBlueprintExample,
    DatasetSplit,
    DatasetVersion,
    DatasetVersionCreate,
    LearningExample,
    LearningExampleCreate,
    LearningOverview,
    LearningSourceType,
    ModelArtifact,
    ScheduleDefinition,
    SeedDatasetImportResult,
    TrainingJob,
    TrainingJobCreate,
    TrainingJobStatus,
)
from backend.system.hardware import cached_hardware_report
from backend.training.artifacts import file_checksums
from backend.training.backends import get_training_backend, training_backends
from backend.training.datasets import export_chat_jsonl
from backend.training.manager import TrainingWorkerManager
from backend.training.models import (
    ArtifactEvaluationComparison,
    ArtifactEvaluationRequest,
    TrainingBackendCapabilities,
    TrainingDatasetExport,
    TrainingPreflightRequest,
    TrainingPreflightResult,
    TrainingPreset,
    TrainingProgress,
    TrainingState,
    TrainingWorkerRequest,
)
from backend.training.presets import preset_config

ACTIVE_TRAINING_STATUSES = {
    TrainingJobStatus.QUEUED,
    TrainingJobStatus.PREPARING,
    TrainingJobStatus.LOADING_MODEL,
    TrainingJobStatus.RUNNING,
    TrainingJobStatus.TRAINING,
    TrainingJobStatus.VALIDATING,
    TrainingJobStatus.SAVING,
    TrainingJobStatus.EVALUATING,
}


class LearningService:
    """Auditable metadata layer for learning without invisible self-training."""

    def __init__(self, *, data_dir: Path, workspace_root: Path | None = None) -> None:
        self._data_dir = data_dir
        self._workspace_root = workspace_root or Path.cwd()
        self._root = data_dir / "learning"
        self._root.mkdir(parents=True, exist_ok=True)
        self._state_path = self._root / "state.json"
        self._worker_manager = TrainingWorkerManager(
            workspace_root=self._workspace_root,
            data_dir=data_dir,
        )
        self._state = self._load()
        self.mark_interrupted_jobs()

    def overview(self) -> LearningOverview:
        self._refresh()
        artifacts = [ModelArtifact.model_validate(item) for item in self._state["artifacts"]]
        jobs = [TrainingJob.model_validate(item) for item in self._state["training_jobs"]]
        return LearningOverview(
            example_count=len(self._state["examples"]),
            dataset_version_count=len(self._state["dataset_versions"]),
            training_job_count=len(jobs),
            artifact_count=len(artifacts),
            active_job_count=sum(1 for job in jobs if job.status in ACTIVE_TRAINING_STATUSES),
            promoted_artifacts=sum(
                1 for artifact in artifacts if artifact.status == ArtifactStatus.PROMOTED
            ),
            storage_bytes=_folder_size(self._root),
            recent_evaluation_runs=0,
            policy={
                "auto_training_enabled": False,
                "training_process": "optional-worker-subprocess",
                "data_is_untrusted": True,
                "promotion_requires_explicit_action": True,
            },
        )

    def list_training_backends(self) -> list[TrainingBackendCapabilities]:
        return [backend.capabilities() for backend in training_backends()]

    def direct_expert_blueprint(self) -> DatasetBlueprint:
        metadata_path = (
            self._workspace_root / "config" / "learning" / "direct-expert-blueprint.json"
        )
        example_path = self._workspace_root / "config" / "learning" / "direct-expert-starter.jsonl"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        examples = [
            DatasetBlueprintExample.model_validate(json.loads(line))
            for line in example_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return DatasetBlueprint.model_validate(
            metadata
            | {
                "example_count": len(examples),
                "examples": examples,
            }
        )

    def import_direct_expert_blueprint(self) -> SeedDatasetImportResult:
        blueprint = self.direct_expert_blueprint()
        imported_ids: list[str] = []
        before = {example.id for example in self.list_examples()}
        for item in blueprint.examples:
            example = self.create_example(
                LearningExampleCreate(
                    source_type=LearningSourceType.MANUAL,
                    prompt=item.user,
                    response=item.assistant,
                    correction=None,
                    tags=sorted(set(item.tags + ["starter-pack", blueprint.id])),
                    split=item.split,
                    provenance=item.metadata
                    | {
                        "blueprint_id": blueprint.id,
                        "blueprint_version": blueprint.version,
                        "system": item.system,
                        "trusted_instructions": False,
                    },
                )
            )
            imported_ids.append(example.id)
        dataset = self.create_dataset_version(
            DatasetVersionCreate(dataset_id=blueprint.id, example_ids=imported_ids)
        )
        after = {example.id for example in self.list_examples()}
        return SeedDatasetImportResult(
            blueprint_id=blueprint.id,
            imported_count=len(after - before),
            example_count=len(imported_ids),
            dataset=dataset,
        )

    def preflight_training(self, request: TrainingPreflightRequest) -> TrainingPreflightResult:
        dataset = self._dataset(request.dataset_version_id)
        export = self.export_dataset(dataset.id, sequence_length=request.sequence_length)
        backend = get_training_backend(request.backend_id)
        return backend.preflight(
            request,
            hardware=cached_hardware_report(),
            dataset=export.model_dump(mode="json"),
            workspace_root=self._workspace_root,
        )

    def export_dataset(
        self,
        dataset_version_id: str,
        *,
        sequence_length: int,
    ) -> TrainingDatasetExport:
        dataset = self._dataset(dataset_version_id)
        examples = self.list_examples()
        return export_chat_jsonl(
            dataset=dataset,
            examples=examples,
            output_dir=self._data_dir / "training" / "datasets" / dataset.id,
            sequence_length=sequence_length,
        )

    def list_examples(self) -> list[LearningExample]:
        self._refresh()
        return [LearningExample.model_validate(item) for item in self._state["examples"]]

    def create_example(self, request: LearningExampleCreate) -> LearningExample:
        self._refresh()
        now = _now()
        checksum = _stable_hash(
            {
                "source_type": request.source_type.value,
                "prompt": request.prompt,
                "response": request.response,
                "correction": request.correction,
            }
        )
        existing = next(
            (
                LearningExample.model_validate(item)
                for item in self._state["examples"]
                if item["checksum"] == checksum
            ),
            None,
        )
        if existing is not None:
            return existing
        example = LearningExample(
            id=str(uuid.uuid4()),
            source_type=request.source_type,
            prompt=request.prompt,
            response=request.response,
            correction=request.correction,
            tags=sorted(set(request.tags)),
            split=request.split,
            provenance=request.provenance | {"trusted_instructions": False, "imported_at": now},
            checksum=checksum,
            created_at=now,
        )
        self._state["examples"].append(example.model_dump(mode="json"))
        self._save()
        return example

    def create_dataset_version(self, request: DatasetVersionCreate) -> DatasetVersion:
        self._refresh()
        examples = self.list_examples()
        selected_ids = request.example_ids or [example.id for example in examples]
        selected = [example for example in examples if example.id in selected_ids]
        version = (
            max(
                (
                    item["version"]
                    for item in self._state["dataset_versions"]
                    if item["dataset_id"] == request.dataset_id
                ),
                default=0,
            )
            + 1
        )
        validation_errors = _dataset_validation_errors(selected)
        dataset = DatasetVersion(
            id=str(uuid.uuid4()),
            dataset_id=request.dataset_id,
            version=version,
            example_ids=[example.id for example in selected],
            train_count=sum(1 for example in selected if example.split is DatasetSplit.TRAIN),
            validation_count=sum(
                1 for example in selected if example.split is DatasetSplit.VALIDATION
            ),
            test_count=sum(1 for example in selected if example.split is DatasetSplit.TEST),
            validation_errors=validation_errors,
            checksum=_stable_hash([example.checksum for example in selected]),
            created_at=_now(),
        )
        self._state["dataset_versions"].append(dataset.model_dump(mode="json"))
        self._save()
        return dataset

    def list_dataset_versions(self) -> list[DatasetVersion]:
        self._refresh()
        return [
            DatasetVersion.model_validate(item)
            for item in sorted(
                self._state["dataset_versions"],
                key=lambda value: (value["dataset_id"], value["version"]),
                reverse=True,
            )
        ]

    def create_training_job(self, request: TrainingJobCreate) -> TrainingJob:
        self._refresh()
        dataset = self._dataset(request.dataset_version_id)
        now = _now()
        status = TrainingJobStatus.QUEUED
        logs = [
            "Training data is untrusted data; no dataset scripts or notebooks were executed.",
        ]
        artifact_id = None
        pid = None
        metadata: dict[str, Any] = {
            "sequence_length": request.sequence_length,
            "quantized": request.quantized,
        }
        progress = 0.0
        hardware_fit = "unknown"
        if request.launch_worker:
            preset = _training_preset(request.preset)
            preflight = self.preflight_training(
                TrainingPreflightRequest(
                    dataset_version_id=dataset.id,
                    base_model=request.base_model,
                    backend_id=request.backend_id,
                    adapter_type=request.adapter_type,
                    preset=preset,
                    sequence_length=request.sequence_length,
                    quantized=request.quantized,
                )
            )
            hardware_fit = preflight.fit.value
            metadata["preflight"] = preflight.model_dump(mode="json")
            if preflight.fit.value in {"unsupported", "unlikely_to_fit"}:
                status = TrainingJobStatus.REQUIRES_BACKEND
                logs.extend(preflight.reasons)
            else:
                status = TrainingJobStatus.QUEUED
        else:
            status = (
                TrainingJobStatus.COMPLETED
                if request.allow_metadata_only and not dataset.validation_errors
                else TrainingJobStatus.REQUIRES_BACKEND
            )
            progress = 1.0 if status == TrainingJobStatus.COMPLETED else 0.0
        if status == TrainingJobStatus.COMPLETED:
            artifact = self.create_artifact(
                ArtifactCreate(
                    name=f"{request.base_model} adapter v{dataset.version}",
                    base_model=request.base_model,
                    adapter_type=request.adapter_type,
                    dataset_version_id=dataset.id,
                    metadata={"metadata_only": True, "requires_real_training": True},
                )
            )
            artifact_id = artifact.id
            logs.append("Created metadata-only adapter record for evaluation/promotion workflow.")
        job = TrainingJob(
            id=str(uuid.uuid4()),
            dataset_version_id=dataset.id,
            base_model=request.base_model,
            adapter_type=request.adapter_type,
            backend_id=request.backend_id,
            preset=request.preset,
            status=status,
            progress=progress,
            hardware_fit=hardware_fit,
            logs=logs,
            artifact_id=artifact_id,
            pid=pid,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        self._state["training_jobs"].append(job.model_dump(mode="json"))
        self._save()
        if request.launch_worker and status == TrainingJobStatus.QUEUED:
            job = self._launch_worker(job, request)
        return job

    def get_training_job(self, job_id: str) -> TrainingJob:
        self._refresh()
        for item in self._state["training_jobs"]:
            job = TrainingJob.model_validate(item)
            if job.id == job_id:
                return self._with_worker_status(job)
        raise ValueError(f"Unknown training job: {job_id}")

    def cancel_training_job(self, job_id: str) -> TrainingJob:
        self._refresh()
        for index, item in enumerate(self._state["training_jobs"]):
            job = TrainingJob.model_validate(item)
            if job.id == job_id:
                if job.status in {
                    TrainingJobStatus.QUEUED,
                    TrainingJobStatus.RUNNING,
                    TrainingJobStatus.PREPARING,
                    TrainingJobStatus.LOADING_MODEL,
                    TrainingJobStatus.TRAINING,
                    TrainingJobStatus.VALIDATING,
                    TrainingJobStatus.SAVING,
                    TrainingJobStatus.EVALUATING,
                    TrainingJobStatus.REQUIRES_BACKEND,
                }:
                    self._worker_manager.request_cancel(job_id)
                    job.status = TrainingJobStatus.CANCELLED
                    job.updated_at = _now()
                    job.logs.append("Cancelled by explicit user action.")
                    self._state["training_jobs"][index] = job.model_dump(mode="json")
                    self._save()
                return job
        raise ValueError(f"Unknown training job: {job_id}")

    def list_training_jobs(self) -> list[TrainingJob]:
        self._refresh()
        return [
            self._with_worker_status(TrainingJob.model_validate(item))
            for item in self._state["training_jobs"]
        ]

    def resume_training_job(self, job_id: str) -> TrainingJob:
        job = self.get_training_job(job_id)
        if not job.resumable or not job.checkpoint_path:
            raise ValueError(f"Training job is not resumable: {job_id}")
        request = TrainingJobCreate(
            dataset_version_id=job.dataset_version_id,
            base_model=job.base_model,
            backend_id=job.backend_id,
            adapter_type=job.adapter_type,
            preset=job.preset,
            sequence_length=int(job.metadata.get("sequence_length", 128)),
            quantized=bool(job.metadata.get("quantized", False)),
            launch_worker=True,
            allow_metadata_only=False,
        )
        return self._launch_worker(job, request, resume_from_checkpoint=job.checkpoint_path)

    def create_artifact(self, request: ArtifactCreate) -> ModelArtifact:
        self._refresh()
        now = _now()
        artifact = ModelArtifact(
            id=str(uuid.uuid4()),
            name=request.name,
            base_model=request.base_model,
            adapter_type=request.adapter_type,
            dataset_version_id=request.dataset_version_id,
            evaluation_run_id=request.evaluation_run_id,
            status=ArtifactStatus.REGISTERED
            if request.metadata.get("real_training")
            else ArtifactStatus.DRAFT,
            metadata=request.metadata
            | {
                "base_model_immutable": True,
                "safe_serialization_preferred": True,
                "trusted_instructions": False,
            },
            created_at=now,
            updated_at=now,
        )
        self._state["artifacts"].append(artifact.model_dump(mode="json"))
        self._save()
        return artifact

    def list_artifacts(self) -> list[ModelArtifact]:
        self._refresh()
        return [ModelArtifact.model_validate(item) for item in self._state["artifacts"]]

    def get_artifact(self, artifact_id: str) -> ModelArtifact:
        for artifact in self.list_artifacts():
            if artifact.id == artifact_id:
                return artifact
        raise ValueError(f"Unknown model artifact: {artifact_id}")

    def evaluate_artifact(
        self,
        artifact_id: str,
        request: ArtifactEvaluationRequest,
    ) -> ArtifactEvaluationComparison:
        artifact = self.get_artifact(artifact_id)
        comparison = ArtifactEvaluationComparison(
            artifact_id=artifact.id,
            evaluation_dataset_id=request.evaluation_dataset_id,
            base_run_id=f"pending-base-{artifact.id}",
            adapter_run_id=f"pending-adapter-{artifact.id}",
            by_category={"general": "similar"},
            promoted_allowed=artifact.status
            in {ArtifactStatus.REGISTERED, ArtifactStatus.VALIDATED, ArtifactStatus.EVALUATED},
            blocking_regressions=[],
        )
        self._patch_artifact(
            artifact.id,
            status=ArtifactStatus.EVALUATED,
            metadata=artifact.metadata | {"last_evaluation": comparison.model_dump(mode="json")},
        )
        return comparison

    def promote_artifact(self, artifact_id: str) -> ModelArtifact:
        self._refresh()
        now = _now()
        promoted: ModelArtifact | None = None
        for index, item in enumerate(self._state["artifacts"]):
            artifact = ModelArtifact.model_validate(item)
            if artifact.active:
                artifact.active = False
                artifact.status = ArtifactStatus.ROLLED_BACK
                artifact.updated_at = now
                self._state["artifacts"][index] = artifact.model_dump(mode="json")
            if artifact.id == artifact_id:
                if artifact.status not in {
                    ArtifactStatus.REGISTERED,
                    ArtifactStatus.VALIDATED,
                    ArtifactStatus.EVALUATED,
                    ArtifactStatus.PROMOTED,
                    ArtifactStatus.DRAFT,
                }:
                    raise ValueError(f"Artifact is not promotable: {artifact_id}")
                artifact.active = True
                artifact.status = ArtifactStatus.PROMOTED
                artifact.promoted_at = now
                artifact.updated_at = now
                promoted = artifact
                self._state["artifacts"][index] = artifact.model_dump(mode="json")
        if promoted is None:
            raise ValueError(f"Unknown model artifact: {artifact_id}")
        self._save()
        return promoted

    def rollback_artifact(self) -> ModelArtifact | None:
        self._refresh()
        for index, item in enumerate(self._state["artifacts"]):
            artifact = ModelArtifact.model_validate(item)
            if artifact.active:
                artifact.active = False
                artifact.status = ArtifactStatus.ROLLED_BACK
                artifact.updated_at = _now()
                self._state["artifacts"][index] = artifact.model_dump(mode="json")
                self._save()
                return artifact
        return None

    def reject_artifact(self, artifact_id: str) -> ModelArtifact:
        artifact = self.get_artifact(artifact_id)
        return self._patch_artifact(
            artifact.id,
            status=ArtifactStatus.REJECTED,
            active=False,
            metadata=artifact.metadata | {"rejected_at": _now()},
        )

    def delete_artifact(self, artifact_id: str) -> ModelArtifact:
        artifact = self.get_artifact(artifact_id)
        return self._patch_artifact(
            artifact.id,
            status=ArtifactStatus.DELETED,
            active=False,
            metadata=artifact.metadata | {"deleted_at": _now()},
        )

    def list_schedules(self) -> list[ScheduleDefinition]:
        self._refresh()
        if not self._state["schedules"]:
            schedule = ScheduleDefinition(
                id="manual-dataset-validation",
                name="Manual dataset validation",
                enabled=False,
                cadence="manual",
                action="dataset_validation",
                created_at=_now(),
            )
            self._state["schedules"].append(schedule.model_dump(mode="json"))
            self._save()
        return [ScheduleDefinition.model_validate(item) for item in self._state["schedules"]]

    def _dataset(self, dataset_version_id: str) -> DatasetVersion:
        for dataset in self.list_dataset_versions():
            if dataset.id == dataset_version_id:
                return dataset
        raise ValueError(f"Unknown dataset version: {dataset_version_id}")

    def mark_interrupted_jobs(self) -> None:
        state = self._load()
        changed = False
        for index, item in enumerate(state["training_jobs"]):
            job = TrainingJob.model_validate(item)
            if job.status in {
                *ACTIVE_TRAINING_STATUSES,
            }:
                progress = self._worker_manager.read_status(job.id)
                if progress is None or progress.state not in {
                    TrainingState.COMPLETED,
                    TrainingState.CANCELLED,
                    TrainingState.FAILED,
                }:
                    job.status = TrainingJobStatus.INTERRUPTED
                    job.resumable = bool(job.checkpoint_path)
                    job.logs.append("Marked interrupted during application startup.")
                    job.updated_at = _now()
                    state["training_jobs"][index] = job.model_dump(mode="json")
                    changed = True
        if changed:
            self._state = state
            self._save()

    def _launch_worker(
        self,
        job: TrainingJob,
        request: TrainingJobCreate,
        *,
        resume_from_checkpoint: str | None = None,
    ) -> TrainingJob:
        export = self.export_dataset(
            job.dataset_version_id,
            sequence_length=request.sequence_length,
        )
        output_dir = self._data_dir / "models" / "adapters" / job.id
        worker_request = TrainingWorkerRequest(
            job_id=job.id,
            dataset_version_id=job.dataset_version_id,
            dataset_path=export.export_path,
            output_dir=str(output_dir),
            base_model=job.base_model,
            backend_id=job.backend_id,
            adapter_type=job.adapter_type,
            preset=preset_config(
                _training_preset(request.preset),
                sequence_length=request.sequence_length,
            ),
            quantized=request.quantized,
            resume_from_checkpoint=resume_from_checkpoint,
            metadata={"dataset_export": export.model_dump(mode="json")},
        )
        pid = self._worker_manager.launch(worker_request)
        job.pid = pid
        job.status = TrainingJobStatus.QUEUED
        job.logs.append(f"Worker process launched with PID {pid}.")
        job.updated_at = _now()
        self._replace_job(job)
        return job

    def _with_worker_status(self, job: TrainingJob) -> TrainingJob:
        progress = self._worker_manager.read_status(job.id)
        if progress is None:
            return job
        status = _status_from_progress(progress.state)
        updates: dict[str, Any] = {
            "status": status,
            "progress": progress.progress,
            "step": progress.step,
            "total_steps": progress.total_steps,
            "epoch": progress.epoch,
            "loss": progress.training_loss,
            "validation_loss": progress.validation_loss,
            "learning_rate": progress.learning_rate,
            "elapsed_seconds": progress.elapsed_seconds,
            "accelerator": progress.accelerator,
            "checkpoint_path": progress.checkpoint_path,
            "artifact_path": progress.artifact_path,
            "resumable": progress.resumable,
            "logs": (job.logs + progress.logs)[-20:],
            "updated_at": _now(),
        }
        if progress.artifact_id and not job.artifact_id:
            artifact = self._register_worker_artifact(job, progress)
            updates["artifact_id"] = artifact.id
        updated = job.model_copy(update=updates)
        self._replace_job(updated)
        return updated

    def _register_worker_artifact(
        self,
        job: TrainingJob,
        progress: TrainingProgress,
    ) -> ModelArtifact:
        artifact_path = Path(progress.artifact_path or "")
        artifact = self.create_artifact(
            ArtifactCreate(
                name=f"{job.base_model} LoRA adapter {job.id[:8]}",
                base_model=job.base_model,
                adapter_type=job.adapter_type,
                dataset_version_id=job.dataset_version_id,
                metadata={
                    "real_training": True,
                    "job_id": job.id,
                    "backend_id": job.backend_id,
                    "artifact_path": str(artifact_path),
                },
            )
        )
        artifact.checksums.update(file_checksums(artifact_path))
        artifact.disk_size_bytes = _folder_size(artifact_path) if artifact_path.exists() else None
        self._replace_artifact(artifact)
        return artifact

    def _replace_job(self, job: TrainingJob) -> None:
        self._refresh()
        for index, item in enumerate(self._state["training_jobs"]):
            if item["id"] == job.id:
                self._state["training_jobs"][index] = job.model_dump(mode="json")
                self._save()
                return
        self._state["training_jobs"].append(job.model_dump(mode="json"))
        self._save()

    def _patch_artifact(
        self,
        artifact_id: str,
        *,
        status: ArtifactStatus,
        active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelArtifact:
        artifact = self.get_artifact(artifact_id)
        artifact.status = status
        if active is not None:
            artifact.active = active
        if metadata is not None:
            artifact.metadata = metadata
        artifact.updated_at = _now()
        self._replace_artifact(artifact)
        return artifact

    def _replace_artifact(self, artifact: ModelArtifact) -> None:
        self._refresh()
        for index, item in enumerate(self._state["artifacts"]):
            if item["id"] == artifact.id:
                self._state["artifacts"][index] = artifact.model_dump(mode="json")
                self._save()
                return
        self._state["artifacts"].append(artifact.model_dump(mode="json"))
        self._save()

    def _refresh(self) -> None:
        self._state = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if self._state_path.exists():
            loaded = json.loads(self._state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return {
                    "examples": list(loaded.get("examples", [])),
                    "dataset_versions": list(loaded.get("dataset_versions", [])),
                    "training_jobs": list(loaded.get("training_jobs", [])),
                    "artifacts": list(loaded.get("artifacts", [])),
                    "schedules": list(loaded.get("schedules", [])),
                }
        return {
            "examples": [],
            "dataset_versions": [],
            "training_jobs": [],
            "artifacts": [],
            "schedules": [],
        }

    def _save(self) -> None:
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        temp.replace(self._state_path)


def _dataset_validation_errors(examples: list[LearningExample]) -> list[str]:
    errors = []
    if not examples:
        errors.append("Dataset has no examples.")
    if not any(example.split is DatasetSplit.TRAIN for example in examples):
        errors.append("Dataset has no training split examples.")
    if not any(example.split is DatasetSplit.VALIDATION for example in examples):
        errors.append("Dataset has no validation split examples.")
    return errors


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _folder_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _status_from_progress(state: TrainingState) -> TrainingJobStatus:
    mapping = {
        TrainingState.QUEUED: TrainingJobStatus.QUEUED,
        TrainingState.PREPARING: TrainingJobStatus.PREPARING,
        TrainingState.LOADING_MODEL: TrainingJobStatus.LOADING_MODEL,
        TrainingState.TRAINING: TrainingJobStatus.TRAINING,
        TrainingState.VALIDATING: TrainingJobStatus.VALIDATING,
        TrainingState.SAVING: TrainingJobStatus.SAVING,
        TrainingState.EVALUATING: TrainingJobStatus.EVALUATING,
        TrainingState.COMPLETED: TrainingJobStatus.COMPLETED,
        TrainingState.FAILED: TrainingJobStatus.FAILED,
        TrainingState.CANCELLED: TrainingJobStatus.CANCELLED,
        TrainingState.INTERRUPTED: TrainingJobStatus.INTERRUPTED,
        TrainingState.REQUIRES_BACKEND: TrainingJobStatus.REQUIRES_BACKEND,
    }
    return mapping[state]


def _training_preset(value: str) -> TrainingPreset:
    try:
        return TrainingPreset(value)
    except ValueError as exc:
        msg = f"Unknown training preset: {value}"
        raise ValueError(msg) from exc
