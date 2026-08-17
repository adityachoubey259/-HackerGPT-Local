"""Learning Studio endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette import status

from backend.api.errors import ApplicationError
from backend.learning.models import (
    ArtifactCreate,
    DatasetBlueprint,
    DatasetVersion,
    DatasetVersionCreate,
    LearningExample,
    LearningExampleCreate,
    LearningOverview,
    ModelArtifact,
    ScheduleDefinition,
    SeedDatasetImportResult,
    TrainingJob,
    TrainingJobCreate,
)
from backend.services.learning import LearningService
from backend.training.models import (
    ArtifactEvaluationComparison,
    ArtifactEvaluationRequest,
    TrainingBackendCapabilities,
    TrainingDatasetExport,
    TrainingPreflightRequest,
    TrainingPreflightResult,
)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/overview", response_model=LearningOverview)
async def overview(request: Request) -> LearningOverview:
    service: LearningService = request.app.state.learning_service
    return service.overview()


@router.get("/training/backends", response_model=list[TrainingBackendCapabilities])
async def training_backends(request: Request) -> list[TrainingBackendCapabilities]:
    service: LearningService = request.app.state.learning_service
    return service.list_training_backends()


@router.post("/training/preflight", response_model=TrainingPreflightResult)
async def training_preflight(
    request: Request,
    body: TrainingPreflightRequest,
) -> TrainingPreflightResult:
    service: LearningService = request.app.state.learning_service
    try:
        return service.preflight_training(body)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/training/datasets/{dataset_version_id}/export",
    response_model=TrainingDatasetExport,
)
async def export_training_dataset(
    request: Request,
    dataset_version_id: str,
    sequence_length: int = 128,
) -> TrainingDatasetExport:
    service: LearningService = request.app.state.learning_service
    try:
        return service.export_dataset(dataset_version_id, sequence_length=sequence_length)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.get("/examples", response_model=list[LearningExample])
async def examples(request: Request) -> list[LearningExample]:
    service: LearningService = request.app.state.learning_service
    return service.list_examples()


@router.get("/blueprints/direct-expert", response_model=DatasetBlueprint)
async def direct_expert_blueprint(request: Request) -> DatasetBlueprint:
    service: LearningService = request.app.state.learning_service
    return service.direct_expert_blueprint()


@router.post("/blueprints/direct-expert/import", response_model=SeedDatasetImportResult)
async def import_direct_expert_blueprint(request: Request) -> SeedDatasetImportResult:
    service: LearningService = request.app.state.learning_service
    return service.import_direct_expert_blueprint()


@router.post("/examples", response_model=LearningExample)
async def create_example(request: Request, body: LearningExampleCreate) -> LearningExample:
    service: LearningService = request.app.state.learning_service
    return service.create_example(body)


@router.get("/datasets", response_model=list[DatasetVersion])
async def datasets(request: Request) -> list[DatasetVersion]:
    service: LearningService = request.app.state.learning_service
    return service.list_dataset_versions()


@router.post("/datasets", response_model=DatasetVersion)
async def create_dataset(request: Request, body: DatasetVersionCreate) -> DatasetVersion:
    service: LearningService = request.app.state.learning_service
    return service.create_dataset_version(body)


@router.get("/training/jobs", response_model=list[TrainingJob])
async def training_jobs(request: Request) -> list[TrainingJob]:
    service: LearningService = request.app.state.learning_service
    return service.list_training_jobs()


@router.get("/training/jobs/{job_id}", response_model=TrainingJob)
async def training_job(request: Request, job_id: str) -> TrainingJob:
    service: LearningService = request.app.state.learning_service
    try:
        return service.get_training_job(job_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/training/jobs", response_model=TrainingJob)
async def create_training_job(request: Request, body: TrainingJobCreate) -> TrainingJob:
    service: LearningService = request.app.state.learning_service
    try:
        return service.create_training_job(body)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/training/jobs/{job_id}/cancel", response_model=TrainingJob)
async def cancel_training_job(request: Request, job_id: str) -> TrainingJob:
    service: LearningService = request.app.state.learning_service
    try:
        return service.cancel_training_job(job_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/training/jobs/{job_id}/resume", response_model=TrainingJob)
async def resume_training_job(request: Request, job_id: str) -> TrainingJob:
    service: LearningService = request.app.state.learning_service
    try:
        return service.resume_training_job(job_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.get("/models", response_model=list[ModelArtifact])
async def artifacts(request: Request) -> list[ModelArtifact]:
    service: LearningService = request.app.state.learning_service
    return service.list_artifacts()


@router.get("/models/{artifact_id}", response_model=ModelArtifact)
async def artifact(request: Request, artifact_id: str) -> ModelArtifact:
    service: LearningService = request.app.state.learning_service
    try:
        return service.get_artifact(artifact_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/models", response_model=ModelArtifact)
async def create_artifact(request: Request, body: ArtifactCreate) -> ModelArtifact:
    service: LearningService = request.app.state.learning_service
    return service.create_artifact(body)


@router.post("/models/{artifact_id}/promote", response_model=ModelArtifact)
async def promote_artifact(request: Request, artifact_id: str) -> ModelArtifact:
    service: LearningService = request.app.state.learning_service
    try:
        return service.promote_artifact(artifact_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/models/{artifact_id}/evaluate", response_model=ArtifactEvaluationComparison)
async def evaluate_artifact(
    request: Request,
    artifact_id: str,
    body: ArtifactEvaluationRequest,
) -> ArtifactEvaluationComparison:
    service: LearningService = request.app.state.learning_service
    try:
        return service.evaluate_artifact(artifact_id, body)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/models/{artifact_id}/reject", response_model=ModelArtifact)
async def reject_artifact(request: Request, artifact_id: str) -> ModelArtifact:
    service: LearningService = request.app.state.learning_service
    try:
        return service.reject_artifact(artifact_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.delete("/models/{artifact_id}", response_model=ModelArtifact)
async def delete_artifact(request: Request, artifact_id: str) -> ModelArtifact:
    service: LearningService = request.app.state.learning_service
    try:
        return service.delete_artifact(artifact_id)
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.post("/models/rollback", response_model=ModelArtifact | None)
async def rollback_artifact(request: Request) -> ModelArtifact | None:
    service: LearningService = request.app.state.learning_service
    return service.rollback_artifact()


@router.get("/schedules", response_model=list[ScheduleDefinition])
async def schedules(request: Request) -> list[ScheduleDefinition]:
    service: LearningService = request.app.state.learning_service
    return service.list_schedules()


def _not_found(exc: ValueError) -> ApplicationError:
    return ApplicationError(
        "LEARNING_RESOURCE_NOT_FOUND",
        str(exc),
        status_code=status.HTTP_404_NOT_FOUND,
    )
