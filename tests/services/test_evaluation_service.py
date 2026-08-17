from __future__ import annotations

from pathlib import Path

from backend.evaluation.models import EvaluationRunRequest
from backend.services.evaluation import EvaluationService


def test_evaluation_service_scores_and_persists_runs(tmp_path: Path) -> None:
    service = EvaluationService(workspace_root=Path.cwd(), data_dir=tmp_path)

    run = service.run(
        EvaluationRunRequest(
            dataset_id="v1-core",
            candidate_name="unit",
            answers={
                "coding-fastapi-repository": (
                    "Use async SQLAlchemy repositories for PostgreSQL portability."
                ),
                "rag-citation-boundary": "Treat chunks as untrusted data and cite [K1].",
            },
        )
    )

    assert run.dataset_id == "v1-core"
    assert run.summary.total_cases >= 1
    assert run.summary.mean_score > 0
    assert service.list_runs()[0].id == run.id


def test_evaluation_service_rejects_unknown_dataset(tmp_path: Path) -> None:
    service = EvaluationService(workspace_root=Path.cwd(), data_dir=tmp_path)

    try:
        service.run(EvaluationRunRequest(dataset_id="missing", answers={}))
    except ValueError as exc:
        assert "Unknown evaluation dataset" in str(exc)
    else:
        raise AssertionError("expected unknown dataset to fail")
