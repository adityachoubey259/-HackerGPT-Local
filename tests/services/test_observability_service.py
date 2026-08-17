from __future__ import annotations

import time
from pathlib import Path

from backend.core.config import AppSettings
from backend.services.observability import LocalMetrics, ObservabilityService


def test_observability_exports_sanitized_diagnostics(tmp_path: Path) -> None:
    metrics = LocalMetrics()
    metrics.record("/api/v1/health", 200, 10.0)
    service = ObservabilityService(
        AppSettings(environment="test"),
        metrics,
        workspace_root=Path.cwd(),
        startup_monotonic=time.monotonic() - 1,
    )

    export = service.diagnostic_export()
    text = str(export).lower()

    assert export["redaction"]["secrets_excluded"] is True
    assert export["redaction"]["prompts_excluded"] is True
    assert "api_key" not in text
    assert "tool_outputs" not in export
    assert export["metrics"]["requests"] == 1
