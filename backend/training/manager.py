"""Subprocess manager for local training workers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path

from backend.training.models import TrainingProgress, TrainingState, TrainingWorkerRequest


class TrainingWorkerManager:
    def __init__(self, *, workspace_root: Path, data_dir: Path) -> None:
        self._workspace_root = workspace_root
        self._training_root = data_dir / "training"
        self._training_root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        return self._training_root / "jobs" / job_id

    def status_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "status.json"

    def cancel_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "cancel.request"

    def request_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "request.json"

    def launch(self, request: TrainingWorkerRequest) -> int:
        job_dir = self.job_dir(request.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        self.request_path(request.job_id).write_text(
            json.dumps(request.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        self.write_status(
            request.job_id,
            TrainingProgress(
                state=TrainingState.QUEUED,
                logs=["Training worker queued."],
                accelerator="unknown",
            ),
        )
        log_path = job_dir / "worker.log"
        env = _worker_env(os.environ)
        with log_path.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(  # noqa: S603
                [
                    sys.executable,
                    "-m",
                    "backend.training.worker",
                    "--request",
                    str(self.request_path(request.job_id)),
                    "--status",
                    str(self.status_path(request.job_id)),
                    "--cancel",
                    str(self.cancel_path(request.job_id)),
                ],
                cwd=self._workspace_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        (job_dir / "worker.pid").write_text(str(process.pid), encoding="utf-8")
        return process.pid

    def read_status(self, job_id: str) -> TrainingProgress | None:
        path = self.status_path(job_id)
        if not path.exists():
            return None
        return TrainingProgress.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def write_status(self, job_id: str, progress: TrainingProgress) -> None:
        path = self.status_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(progress.model_dump(mode="json"), indent=2), encoding="utf-8")
        temp.replace(path)

    def request_cancel(self, job_id: str) -> None:
        path = self.cancel_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(time.time()), encoding="utf-8")


def _worker_env(source: Mapping[str, str]) -> dict[str, str]:
    allowed_prefixes = ("PATH", "PYTHONPATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME")
    env = {key: value for key, value in source.items() if key.upper() in allowed_prefixes}
    env["HACKERGPT_TRAINING_WORKER"] = "1"
    return env
