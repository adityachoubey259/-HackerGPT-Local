"""Local-only observability, metrics, and sanitized diagnostics."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.core.config import AppSettings
from backend.core.version import APP_VERSION
from backend.system.hardware import HardwareReport, cached_hardware_report


@dataclass
class LocalMetrics:
    requests: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    routes: Counter[str] = field(default_factory=Counter)

    def record(self, route: str, status_code: int, duration_ms: float) -> None:
        self.requests += 1
        self.total_latency_ms += duration_ms
        self.routes[route] += 1
        if status_code >= 500:
            self.errors += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "errors": self.errors,
            "mean_latency_ms": round(self.total_latency_ms / self.requests, 3)
            if self.requests
            else 0.0,
            "routes": dict(self.routes.most_common(20)),
        }


class ObservabilityService:
    def __init__(
        self,
        settings: AppSettings,
        metrics: LocalMetrics,
        *,
        workspace_root: Path,
        startup_monotonic: float,
    ) -> None:
        self._settings = settings
        self._metrics = metrics
        self._workspace_root = workspace_root
        self._startup_monotonic = startup_monotonic

    def metrics(self) -> dict[str, Any]:
        return self._metrics.snapshot()

    def diagnostic_export(self) -> dict[str, Any]:
        hardware = cached_hardware_report()
        return {
            "application": {
                "name": "HackerGPT Local",
                "version": APP_VERSION,
                "environment": self._settings.environment,
                "uptime_seconds": round(time.monotonic() - self._startup_monotonic, 3),
            },
            "hardware": _safe_hardware(hardware),
            "configuration": {
                "database_type": self._settings.database.type,
                "serve_frontend": self._settings.frontend.serve_static,
                "network_access": self._settings.network_access,
                "debug": self._settings.debug,
            },
            "paths": {
                "workspace": str(self._workspace_root),
                "data_dir": str(self._settings.paths.data_dir),
            },
            "metrics": self.metrics(),
            "redaction": {
                "secrets_excluded": True,
                "prompts_excluded": True,
                "documents_excluded": True,
                "tool_outputs_excluded": True,
            },
        }


def _safe_hardware(hardware: HardwareReport) -> dict[str, Any]:
    return {
        "operating_system": hardware.operating_system,
        "architecture": hardware.architecture,
        "cpu_model": hardware.cpu.model,
        "logical_processors": hardware.cpu.logical_processors,
        "memory_total_bytes": hardware.memory.total_bytes,
        "gpu_count": len(hardware.gpus),
        "gpus": [
            {
                "name": gpu.name,
                "vendor": gpu.vendor,
                "vram_total_bytes": gpu.vram_total_bytes,
                "driver_version": gpu.driver_version,
            }
            for gpu in hardware.gpus
        ],
        "acceleration": hardware.acceleration.model_dump(mode="json"),
        "detection_warnings": hardware.detection_warnings,
    }
