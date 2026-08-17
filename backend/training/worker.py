"""Optional Transformers/PEFT training worker subprocess."""

from __future__ import annotations

import argparse
import importlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from backend.training.artifacts import file_checksums
from backend.training.models import (
    TrainingArtifactManifest,
    TrainingProgress,
    TrainingState,
    TrainingWorkerRequest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="HackerGPT Local training worker")
    parser.add_argument("--request", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--cancel", required=True)
    args = parser.parse_args()
    request = TrainingWorkerRequest.model_validate(
        json.loads(Path(args.request).read_text(encoding="utf-8"))
    )
    return run_worker(request, status_path=Path(args.status), cancel_path=Path(args.cancel))


def run_worker(
    request: TrainingWorkerRequest,
    *,
    status_path: Path,
    cancel_path: Path,
) -> int:
    started = time.perf_counter()

    def update(progress: TrainingProgress) -> None:
        progress.elapsed_seconds = round(time.perf_counter() - started, 3)
        _write_status(status_path, progress)

    try:
        update(
            TrainingProgress(
                state=TrainingState.PREPARING,
                progress=0.05,
                logs=["Preparing training dataset."],
            )
        )
        if cancel_path.exists():
            return _cancelled(status_path, started)
        try:
            datasets = importlib.import_module("datasets")
            peft = importlib.import_module("peft")
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            update(
                TrainingProgress(
                    state=TrainingState.FAILED,
                    progress=0,
                    error=f"Training dependencies are not installed: {exc.name}",
                    logs=['Install optional dependencies with: pip install -e ".[training]"'],
                )
            )
            return 1
        datasets = cast(Any, datasets)
        peft = cast(Any, peft)
        torch = cast(Any, torch)
        transformers = cast(Any, transformers)
        accelerator = "cuda" if bool(torch.cuda.is_available()) else "cpu"
        update(
            TrainingProgress(
                state=TrainingState.LOADING_MODEL,
                progress=0.15,
                accelerator=accelerator,
                logs=[f"Loading base model {request.base_model}."],
            )
        )
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            request.base_model,
            use_fast=True,
            trust_remote_code=False,
            local_files_only=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = transformers.AutoModelForCausalLM.from_pretrained(
            request.base_model,
            trust_remote_code=False,
            local_files_only=True,
        )
        lora_config = peft.LoraConfig(
            r=request.preset.lora_rank,
            lora_alpha=request.preset.lora_alpha,
            lora_dropout=request.preset.lora_dropout,
            task_type=peft.TaskType.CAUSAL_LM,
        )
        model = peft.get_peft_model(model, lora_config)
        records = _load_records(Path(request.dataset_path))
        raw_dataset = datasets.Dataset.from_list(records)

        def tokenize(item: dict[str, Any]) -> dict[str, Any]:
            text = _messages_to_text(cast(list[dict[str, str]], item["messages"]))
            encoded = tokenizer(
                text,
                truncation=True,
                max_length=request.preset.sequence_length,
                padding="max_length",
            )
            encoded["labels"] = list(encoded["input_ids"])
            return cast(dict[str, Any], encoded)

        tokenized = raw_dataset.map(tokenize, remove_columns=raw_dataset.column_names)
        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        args = transformers.TrainingArguments(
            output_dir=str(output_dir / "checkpoints"),
            max_steps=request.preset.max_steps,
            num_train_epochs=request.preset.epochs,
            per_device_train_batch_size=request.preset.batch_size,
            gradient_accumulation_steps=request.preset.gradient_accumulation_steps,
            learning_rate=request.preset.learning_rate,
            logging_steps=1,
            save_steps=max(1, request.preset.max_steps),
            report_to=[],
        )
        trainer = transformers.Trainer(
            model=model,
            args=args,
            train_dataset=tokenized,
            data_collator=transformers.DataCollatorForLanguageModeling(tokenizer, mlm=False),
            callbacks=[CancelCallback(cancel_path, status_path, started)],
        )
        update(
            TrainingProgress(
                state=TrainingState.TRAINING,
                progress=0.3,
                total_steps=request.preset.max_steps,
                accelerator=accelerator,
                logs=["Training started."],
            )
        )
        trainer.train(resume_from_checkpoint=request.resume_from_checkpoint)
        if cancel_path.exists():
            return _cancelled(status_path, started)
        update(
            TrainingProgress(
                state=TrainingState.SAVING,
                progress=0.9,
                total_steps=request.preset.max_steps,
                step=request.preset.max_steps,
                accelerator=accelerator,
                logs=["Saving adapter artifact."],
            )
        )
        adapter_dir = output_dir / "adapter"
        model.save_pretrained(adapter_dir, safe_serialization=True)
        tokenizer.save_pretrained(adapter_dir)
        artifact_id = str(uuid.uuid4())
        manifest = TrainingArtifactManifest(
            artifact_id=artifact_id,
            job_id=request.job_id,
            base_model=request.base_model,
            adapter_type=request.adapter_type,
            backend_id=request.backend_id,
            artifact_path=str(adapter_dir),
            dataset_version_id=request.dataset_version_id,
            checksums=file_checksums(adapter_dir),
            created_at=datetime.now(UTC).isoformat(),
            metadata={"safe_serialization_preferred": True},
        )
        (output_dir / "artifact.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        update(
            TrainingProgress(
                state=TrainingState.COMPLETED,
                progress=1.0,
                step=request.preset.max_steps,
                total_steps=request.preset.max_steps,
                accelerator=accelerator,
                artifact_id=artifact_id,
                artifact_path=str(adapter_dir),
                logs=["Training completed and adapter manifest written."],
            )
        )
        return 0
    except KeyboardInterrupt:
        return _cancelled(status_path, started)
    except Exception as exc:  # noqa: BLE001
        update(
            TrainingProgress(
                state=TrainingState.FAILED,
                progress=0,
                error=str(exc),
                logs=["Training worker failed."],
            )
        )
        return 1


class CancelCallback:
    def __init__(self, cancel_path: Path, status_path: Path, started: float) -> None:
        self._cancel_path = cancel_path
        self._status_path = status_path
        self._started = started

    def on_step_end(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
        if self._cancel_path.exists():
            control.should_training_stop = True
            control.should_save = True
        progress = 0.3
        max_steps = int(getattr(state, "max_steps", 0) or 0)
        step = int(getattr(state, "global_step", 0) or 0)
        if max_steps:
            progress = min(0.9, 0.3 + (step / max_steps) * 0.55)
        loss = None
        if getattr(state, "log_history", None):
            last = state.log_history[-1]
            if isinstance(last, dict) and isinstance(last.get("loss"), float):
                loss = last["loss"]
        _write_status(
            self._status_path,
            TrainingProgress(
                state=TrainingState.TRAINING,
                progress=progress,
                step=step,
                total_steps=max_steps or None,
                training_loss=loss,
                elapsed_seconds=round(time.perf_counter() - self._started, 3),
                logs=["Training step completed."],
            ),
        )
        return control


def _load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            loaded = json.loads(line)
            if isinstance(loaded, dict):
                records.append(loaded)
    if not records:
        msg = "Training dataset is empty."
        raise ValueError(msg)
    return records


def _messages_to_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{item['role']}: {item['content']}" for item in messages)


def _write_status(path: Path, progress: TrainingProgress) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(progress.model_dump(mode="json"), indent=2), encoding="utf-8")
    temp.replace(path)


def _cancelled(status_path: Path, started: float) -> int:
    _write_status(
        status_path,
        TrainingProgress(
            state=TrainingState.CANCELLED,
            progress=0,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            logs=["Training cancelled."],
        ),
    )
    return 130


if __name__ == "__main__":
    raise SystemExit(main())
