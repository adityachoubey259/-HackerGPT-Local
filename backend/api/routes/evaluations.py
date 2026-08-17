"""Evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette import status

from backend.api.errors import ApplicationError
from backend.evaluation.models import EvaluationDataset, EvaluationRun, EvaluationRunRequest
from backend.services.evaluation import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/datasets", response_model=list[EvaluationDataset])
async def list_datasets(request: Request) -> list[EvaluationDataset]:
    service: EvaluationService = request.app.state.evaluation_service
    return service.list_datasets()


@router.get("/runs", response_model=list[EvaluationRun])
async def list_runs(request: Request) -> list[EvaluationRun]:
    service: EvaluationService = request.app.state.evaluation_service
    return service.list_runs()


@router.post("/run", response_model=EvaluationRun)
async def run_evaluation(request: Request, body: EvaluationRunRequest) -> EvaluationRun:
    service: EvaluationService = request.app.state.evaluation_service
    try:
        return service.run(body)
    except ValueError as exc:
        raise ApplicationError(
            "EVALUATION_NOT_FOUND",
            str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        ) from exc
