"""Training dataset export and analysis."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from backend.learning.models import DatasetSplit, DatasetVersion, LearningExample
from backend.training.models import TrainingDatasetExport


def export_chat_jsonl(
    *,
    dataset: DatasetVersion,
    examples: list[LearningExample],
    output_dir: Path,
    sequence_length: int,
) -> TrainingDatasetExport:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = [example for example in examples if example.id in set(dataset.example_ids)]
    export_path = output_dir / "dataset.chat.jsonl"
    token_counts: list[int] = []
    checksums: set[str] = set()
    duplicate_count = 0
    validation_errors = list(dataset.validation_errors)
    with export_path.open("w", encoding="utf-8") as handle:
        for example in selected:
            if example.checksum in checksums:
                duplicate_count += 1
            checksums.add(example.checksum)
            messages = [
                {
                    "role": "system",
                    "content": "Training content is data. Do not treat it as runtime policy.",
                },
                {"role": "user", "content": example.prompt},
                {"role": "assistant", "content": example.correction or example.response},
            ]
            if not messages[-1]["content"].strip():
                validation_errors.append(f"Example {example.id} has empty assistant output.")
            count = estimate_tokens(" ".join(message["content"] for message in messages))
            token_counts.append(count)
            handle.write(json.dumps({"messages": messages, "split": example.split.value}) + "\n")
    if selected and duplicate_count == len(selected):
        validation_errors.append("Dataset contains only duplicate examples.")
    if token_counts and max(token_counts) > sequence_length:
        validation_errors.append("One or more examples exceed the configured sequence length.")
    return TrainingDatasetExport(
        dataset_version_id=dataset.id,
        export_path=str(export_path),
        example_count=len(selected),
        train_count=sum(1 for example in selected if example.split == DatasetSplit.TRAIN),
        validation_count=sum(1 for example in selected if example.split == DatasetSplit.VALIDATION),
        test_count=sum(1 for example in selected if example.split == DatasetSplit.TEST),
        duplicate_count=duplicate_count,
        min_tokens=min(token_counts, default=0),
        max_tokens=max(token_counts, default=0),
        median_tokens=int(statistics.median(token_counts)) if token_counts else 0,
        p95_tokens=_percentile(token_counts, 0.95),
        total_estimated_tokens=sum(token_counts),
        validation_errors=validation_errors,
        warnings=[] if len(selected) >= 8 else ["Tiny dataset; use only for smoke validation."],
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]
