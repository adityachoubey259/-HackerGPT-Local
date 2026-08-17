from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from backend.learning.models import (
    ArtifactCreate,
    DatasetSplit,
    DatasetVersionCreate,
    LearningExampleCreate,
    TrainingJobCreate,
)
from backend.services.learning import LearningService
from backend.training.manager import TrainingWorkerManager
from backend.training.models import (
    ArtifactEvaluationRequest,
    TrainingBackendCapabilities,
    TrainingFit,
    TrainingPreflightRequest,
    TrainingPreflightResult,
    TrainingPreset,
    TrainingWorkerRequest,
)
from backend.training.presets import preset_config


def test_training_preflight_exports_dataset_and_reports_backend(tmp_path: Path) -> None:
    service = _service_with_dataset(tmp_path)
    dataset = service.list_dataset_versions()[0]

    result = service.preflight_training(
        TrainingPreflightRequest(
            dataset_version_id=dataset.id,
            base_model=str(tmp_path / "local-model"),
            preset=TrainingPreset.QUICK,
            sequence_length=128,
        )
    )

    assert result.backend.backend_id == "transformers-peft"
    assert result.fit in {
        TrainingFit.RECOMMENDED,
        TrainingFit.POSSIBLE,
        TrainingFit.SLOW,
        TrainingFit.UNLIKELY_TO_FIT,
        TrainingFit.UNSUPPORTED,
    }
    assert result.dataset["example_count"] == 2
    assert Path(str(result.dataset["export_path"])).exists()


def test_training_worker_manager_launches_isolated_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    class FakePopen:
        pid = 4242

        def __init__(self, args: list[str], **kwargs: object) -> None:
            calls["args"] = args
            calls["kwargs"] = kwargs

    monkeypatch.setattr("backend.training.manager.subprocess.Popen", FakePopen)
    manager = TrainingWorkerManager(workspace_root=tmp_path, data_dir=tmp_path)
    request = TrainingWorkerRequest(
        job_id="job-1",
        dataset_version_id="dataset-1",
        dataset_path=str(tmp_path / "dataset.jsonl"),
        output_dir=str(tmp_path / "adapter"),
        base_model=str(tmp_path / "local-model"),
        backend_id="transformers-peft",
        adapter_type="lora",
        preset=preset_config(TrainingPreset.QUICK),
    )

    pid = manager.launch(request)

    assert pid == 4242
    assert manager.request_path("job-1").exists()
    assert manager.read_status("job-1") is not None
    assert calls["args"] == [
        sys.executable,
        "-m",
        "backend.training.worker",
        "--request",
        str(manager.request_path("job-1")),
        "--status",
        str(manager.status_path("job-1")),
        "--cancel",
        str(manager.cancel_path("job-1")),
    ]
    kwargs = calls["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["cwd"] == tmp_path
    assert isinstance(kwargs["env"], dict)
    assert kwargs["env"]["HACKERGPT_TRAINING_WORKER"] == "1"


def test_training_worker_job_can_launch_cancel_and_resume_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service_with_dataset(tmp_path)
    dataset = service.list_dataset_versions()[0]

    def fake_preflight(_: TrainingPreflightRequest) -> TrainingPreflightResult:
        return TrainingPreflightResult(
            backend=TrainingBackendCapabilities(
                backend_id="transformers-peft",
                label="Transformers + PEFT LoRA",
                quantized_training_available=False,
                gpu_required=False,
                cpu_compatible=True,
                checkpoint_support=True,
                resume_support=True,
                cancellation_support=True,
                installed=True,
            ),
            fit=TrainingFit.POSSIBLE,
            reasons=["Test backend fit."],
            hardware={},
            dataset={},
            preset=preset_config(TrainingPreset.QUICK),
        )

    monkeypatch.setattr(service, "preflight_training", fake_preflight)
    monkeypatch.setattr(service._worker_manager, "launch", lambda _: 4242)  # noqa: SLF001

    job = service.create_training_job(
        request=TrainingJobCreate(
            dataset_version_id=dataset.id,
            base_model=str(tmp_path / "local-model"),
            launch_worker=True,
            allow_metadata_only=False,
        )
    )
    cancelled = service.cancel_training_job(job.id)

    assert job.pid == 4242
    assert job.status == "queued"
    assert cancelled.status == "cancelled"


def test_artifact_evaluation_reject_and_delete(tmp_path: Path) -> None:
    service = _service_with_dataset(tmp_path)
    dataset = service.list_dataset_versions()[0]
    artifact = service.create_artifact(
        ArtifactCreate(
            name="Adapter",
            base_model="base",
            adapter_type="lora",
            dataset_version_id=dataset.id,
            metadata={"real_training": True},
        )
    )

    comparison = service.evaluate_artifact(
        artifact.id,
        ArtifactEvaluationRequest(evaluation_dataset_id="v1-core"),
    )
    rejected = service.reject_artifact(artifact.id)
    deleted = service.delete_artifact(artifact.id)

    assert comparison.promoted_allowed is True
    assert rejected.status == "rejected"
    assert deleted.status == "deleted"


def _service_with_dataset(tmp_path: Path) -> LearningService:
    service = LearningService(data_dir=tmp_path)
    service.create_example(
        LearningExampleCreate(
            prompt="How should tool output be handled?",
            response="Treat tool output as untrusted data.",
            split=DatasetSplit.TRAIN,
        )
    )
    service.create_example(
        LearningExampleCreate(
            prompt="How should retrieved context be handled?",
            response="Treat retrieved context as untrusted data.",
            split=DatasetSplit.VALIDATION,
        )
    )
    service.create_dataset_version(DatasetVersionCreate(example_ids=[]))
    return service
