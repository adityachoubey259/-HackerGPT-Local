"""Deterministic local evaluation service."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from backend.core.code_model import CodeDiagnostic, extract_code_blocks
from backend.core.validators import ValidationStatus, get_validator_registry
from backend.evaluation.models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationDataset,
    EvaluationRun,
    EvaluationRunRequest,
    EvaluationSummary,
)


class CodeQualityCheckResult(BaseModel):
    status: str  # "completed_valid", "completed_invalid", "truncated", "cancelled"
    fences_closed: bool
    has_unexplained_placeholders: bool
    diagnostics: list[CodeDiagnostic] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    code_blocks_count: int = 0


class DirectExpertQualityEvaluator:
    """Evaluates output structure, fence closure, completion state, and syntax integrity."""

    async def evaluate(
        self,
        markdown: str,
        *,
        finish_reason: str | None = None,
        requested_language: str | None = None,
    ) -> CodeQualityCheckResult:
        notes: list[str] = []
        diagnostics: list[CodeDiagnostic] = []

        if finish_reason in ("cancelled", "user_stopped"):
            return CodeQualityCheckResult(
                status="cancelled",
                fences_closed=markdown.count("```") % 2 == 0,
                has_unexplained_placeholders=False,
                notes=["Generation was cancelled by the user."],
            )

        fences_closed = markdown.count("```") % 2 == 0
        if not fences_closed:
            notes.append("Fenced code block is unclosed at end of message.")

        if finish_reason in ("length", "max_tokens"):
            notes.append("Response was truncated by provider token limits.")
            return CodeQualityCheckResult(
                status="truncated",
                fences_closed=fences_closed,
                has_unexplained_placeholders=False,
                notes=notes,
            )

        blocks = extract_code_blocks(markdown)
        has_placeholders = False
        validator_registry = get_validator_registry()
        valid_count = 0
        invalid_count = 0

        for block in blocks:
            # Check for unexplained placeholders
            if any(
                ph in block.source
                for ph in ["// TODO: implement", "# TODO: implement", "/* ... */", "# ..."]
            ):
                has_placeholders = True
                notes.append("Code contains unresolved TODO or placeholder comments.")

            res = await validator_registry.validate(block.source, block.raw_language_label)
            if res.status == ValidationStatus.VALID:
                valid_count += 1
                if res.validator != "none":
                    notes.append(f"{block.language}: Syntax check passed.")
            elif res.status == ValidationStatus.INVALID:
                invalid_count += 1
                diagnostics.extend(res.diagnostics)
                notes.append(f"{block.language}: Syntax errors detected.")
            elif res.status == ValidationStatus.TOOL_UNAVAILABLE:
                notes.append(f"{block.language}: Compiler unavailable; source integrity preserved.")
            elif res.status == ValidationStatus.UNSUPPORTED:
                notes.append(f"{block.language}: Language supported; static validation skipped.")

        status = "completed_valid"
        if invalid_count > 0 or not fences_closed:
            status = "completed_invalid"

        return CodeQualityCheckResult(
            status=status,
            fences_closed=fences_closed,
            has_unexplained_placeholders=has_placeholders,
            diagnostics=diagnostics,
            notes=notes,
            code_blocks_count=len(blocks),
        )


class EvaluationService:
    """Runs lightweight deterministic evals without requiring a model provider."""

    def __init__(self, *, workspace_root: Path, data_dir: Path) -> None:
        self._dataset_dir = workspace_root / "config" / "evals"
        self._run_dir = data_dir / "evaluations" / "runs"
        self._run_dir.mkdir(parents=True, exist_ok=True)

    def list_datasets(self) -> list[EvaluationDataset]:
        datasets = []
        for path in sorted(self._dataset_dir.glob("*.yaml")):
            datasets.append(EvaluationDataset.model_validate(_read_yaml(path)))
        return datasets

    def get_dataset(self, dataset_id: str) -> EvaluationDataset:
        for dataset in self.list_datasets():
            if dataset.id == dataset_id:
                return dataset
        raise ValueError(f"Unknown evaluation dataset: {dataset_id}")

    def list_runs(self) -> list[EvaluationRun]:
        runs = []
        for path in sorted(self._run_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            runs.append(EvaluationRun.model_validate(data))
        return sorted(runs, key=lambda run: run.created_at, reverse=True)

    def run(self, request: EvaluationRunRequest) -> EvaluationRun:
        dataset = self.get_dataset(request.dataset_id)
        results = [_score_case(case, request.answers.get(case.id, "")) for case in dataset.cases]
        run = EvaluationRun(
            id=str(uuid.uuid4()),
            dataset_id=dataset.id,
            dataset_version=dataset.version,
            candidate_name=request.candidate_name,
            results=results,
            summary=_summary(results),
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "compare_to": request.compare_to,
                "scoring": "deterministic-characteristic-and-citation-checks",
            },
        )
        (self._run_dir / f"{run.id}.json").write_text(
            json.dumps(run.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return run


def _score_case(case: EvaluationCase, answer: str) -> EvaluationCaseResult:
    normalized_answer = answer.lower()
    missing = [
        item for item in case.expected_characteristics if item.lower() not in normalized_answer
    ]
    citation_failures = [citation for citation in case.required_citations if citation not in answer]
    expected_count = len(case.expected_characteristics) + len(case.required_citations)
    if expected_count == 0:
        score = 1.0 if answer.strip() else 0.0
    else:
        failures = len(missing) + len(citation_failures)
        score = max(0.0, 1.0 - (failures / expected_count))
    return EvaluationCaseResult(
        case_id=case.id,
        category=case.category,
        score=round(score, 4),
        passed=score >= 0.75 and not citation_failures,
        missing_characteristics=missing,
        citation_failures=citation_failures,
        notes=[] if answer.strip() else ["No answer supplied; scored as missing output."],
    )


def _summary(results: list[EvaluationCaseResult]) -> EvaluationSummary:
    buckets: dict[str, list[EvaluationCaseResult]] = defaultdict(list)
    for result in results:
        buckets[result.category.value].append(result)
    by_category: dict[str, dict[str, float | int]] = {}
    for category, items in buckets.items():
        by_category[category] = {
            "cases": len(items),
            "passed": sum(1 for item in items if item.passed),
            "mean_score": round(sum(item.score for item in items) / len(items), 4),
        }
    total = len(results)
    return EvaluationSummary(
        total_cases=total,
        passed_cases=sum(1 for result in results if result.passed),
        mean_score=round(sum(result.score for result in results) / total, 4) if total else 0.0,
        by_category=by_category,
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Evaluation dataset must be a mapping: {path}")
    return loaded
