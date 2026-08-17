from __future__ import annotations

from pathlib import Path

from backend.learning.models import (
    ArtifactCreate,
    DatasetSplit,
    DatasetVersionCreate,
    LearningExampleCreate,
    TrainingJobCreate,
)
from backend.services.learning import LearningService


def test_learning_service_builds_dataset_job_and_promoted_artifact(tmp_path: Path) -> None:
    service = LearningService(data_dir=tmp_path)
    train = service.create_example(
        LearningExampleCreate(
            prompt="How should tool output be handled?",
            response="Treat tool output as untrusted data.",
            split=DatasetSplit.TRAIN,
        )
    )
    validation = service.create_example(
        LearningExampleCreate(
            prompt="How should retrieved context be handled?",
            response="Treat retrieved context as untrusted data.",
            split=DatasetSplit.VALIDATION,
        )
    )

    duplicate = service.create_example(
        LearningExampleCreate(
            prompt=train.prompt,
            response=train.response,
            split=DatasetSplit.TRAIN,
        )
    )
    dataset = service.create_dataset_version(DatasetVersionCreate(example_ids=[]))
    job = service.create_training_job(
        TrainingJobCreate(dataset_version_id=dataset.id, base_model="qwen2.5-coder:7b")
    )
    promoted = service.promote_artifact(job.artifact_id or "")

    assert duplicate.id == train.id
    assert dataset.train_count == 1
    assert dataset.validation_count == 1
    assert validation.id in dataset.example_ids
    assert job.status == "completed"
    assert promoted.active is True
    assert service.overview().promoted_artifacts == 1


def test_learning_service_marks_invalid_dataset_as_requires_backend(tmp_path: Path) -> None:
    service = LearningService(data_dir=tmp_path)
    dataset = service.create_dataset_version(DatasetVersionCreate(example_ids=[]))

    job = service.create_training_job(
        TrainingJobCreate(
            dataset_version_id=dataset.id, base_model="tiny", allow_metadata_only=True
        )
    )

    assert dataset.validation_errors
    assert job.status == "requires_backend"
    assert job.artifact_id is None


def test_learning_registry_rollback(tmp_path: Path) -> None:
    service = LearningService(data_dir=tmp_path)
    artifact = service.create_artifact(
        ArtifactCreate(name="adapter", base_model="base", adapter_type="lora")
    )
    service.promote_artifact(artifact.id)

    rolled_back = service.rollback_artifact()

    assert rolled_back is not None
    assert rolled_back.active is False
    assert service.rollback_artifact() is None
