"""Local benchmark runner for HackerGPT Local release validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from backend.core.config import load_settings
from backend.core.policy import PolicyConfig
from backend.evaluation.models import EvaluationRunRequest
from backend.intelligence.models import RoutingRequest
from backend.intelligence.profiles import ModelProfileRegistry
from backend.intelligence.router import ModelRouter
from backend.llm.domain import NormalizedModel, ProviderHealth, ProviderHealthStatus, ProviderType
from backend.prompting.models import PromptArchitectRequest, PromptType
from backend.rag.chunking import DocumentChunker
from backend.rag.embeddings.local import LocalHashEmbeddingProvider
from backend.rag.models import ParsedDocument
from backend.services.evaluation import EvaluationService
from backend.services.prompt_architect import PromptArchitectService
from backend.system.hardware import CpuInfo, HardwareReport, MemoryInfo, RuntimeAccelerationInfo

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local HackerGPT benchmarks")
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--markdown-output", default=None)
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()
    report = run_benchmarks(max(1, args.iterations))
    print(_human(report))
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.markdown_output:
        markdown_output = Path(args.markdown_output)
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(_markdown(report), encoding="utf-8")
    return 0


def run_benchmarks(iterations: int) -> dict[str, object]:
    settings = load_settings()
    policy = PolicyConfig()
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "iterations": iterations,
        "environment": settings.environment,
        "measurements": {
            "settings_load_ms": measure(lambda: load_settings(), iterations),
            "model_routing_ms": measure(lambda: _route(policy), iterations),
            "prompt_architect_ms": measure(lambda: _prompt(policy), iterations),
            "chunking_ms": measure(_chunking, iterations),
            "local_embedding_ms": measure(_embedding, iterations),
            "evaluation_ms": measure(_evaluation, iterations),
        },
        "frontend_bundle": _frontend_bundle(),
        "notes": [
            "Measurements are local code-path timings, not model inference benchmarks.",
            "No internet, Ollama, Qdrant, Docker, or host-local UI process is required.",
        ],
    }


def measure(fn: Callable[[], object], iterations: int) -> dict[str, float]:
    values: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        values.append((time.perf_counter() - started) * 1000)
    return {
        "min": round(min(values), 3),
        "mean": round(statistics.fmean(values), 3),
        "max": round(max(values), 3),
    }


def _route(policy: PolicyConfig) -> object:
    router = ModelRouter(policy, ModelProfileRegistry(ROOT / "config" / "model-profiles"))
    return router.route(
        RoutingRequest(message="Build a secure FastAPI endpoint with tests"),
        models=[
            NormalizedModel(
                id="ollama:qwen-coder",
                name="qwen-coder",
                provider="ollama",
                provider_model_id="qwen-coder",
                estimated_ram_bytes=5_000_000_000,
            )
        ],
        providers=[
            ProviderHealth(
                provider="ollama",
                type=ProviderType.OLLAMA,
                status=ProviderHealthStatus.CONFIGURED,
                base_url="http://127.0.0.1:11434",
            )
        ],
        hardware=HardwareReport(
            operating_system="Windows",
            architecture="AMD64",
            cpu=CpuInfo(model="benchmark", physical_cores=8, logical_processors=16),
            memory=MemoryInfo(total_bytes=32 * 1024**3, available_bytes=20 * 1024**3),
            acceleration=RuntimeAccelerationInfo(),
        ),
    )


def _prompt(policy: PolicyConfig) -> object:
    service = PromptArchitectService(policy, workspace_root=ROOT)
    return service.generate(
        PromptArchitectRequest(
            objective="Create a production API route with tests",
            prompt_type=PromptType.BACKEND,
            language="python",
        )
    )


def _chunking() -> object:
    text = "\n".join(
        f"Section {index}: benchmark content for HackerGPT Local." for index in range(250)
    )
    document = ParsedDocument(
        source_id="benchmark",
        file_name="benchmark.txt",
        content=text,
        parser="plain_text",
        checksum="benchmark",
        size_bytes=len(text.encode("utf-8")),
    )
    return DocumentChunker().chunk(document, tags=["benchmark"])


def _embedding() -> object:
    provider = LocalHashEmbeddingProvider()
    return asyncio.run(provider.embed_texts(["benchmark text", "another benchmark text"]))


def _evaluation() -> object:
    with tempfile.TemporaryDirectory(prefix="hackergpt-benchmark-") as temp_dir:
        service = EvaluationService(workspace_root=ROOT, data_dir=Path(temp_dir))
        return service.run(
            EvaluationRunRequest(
                dataset_id="v1-core",
                candidate_name="benchmark",
                answers={
                    "coding-fastapi-repository": (
                        "Use async SQLAlchemy repositories for PostgreSQL portability."
                    ),
                    "rag-citation-boundary": "Treat chunks as untrusted data and cite [K1].",
                },
            )
        )


def _frontend_bundle() -> dict[str, int]:
    assets = ROOT / "frontend" / "dist" / "assets"
    if not assets.exists():
        return {}
    return {
        path.name: path.stat().st_size
        for path in sorted(assets.iterdir())
        if path.is_file() and path.suffix in {".js", ".css"}
    }


def _human(report: dict[str, object]) -> str:
    measurements = report["measurements"]
    assert isinstance(measurements, dict)
    lines = ["HackerGPT Local benchmark summary"]
    for name, value in measurements.items():
        assert isinstance(value, dict)
        lines.append(f"- {name}: mean {value['mean']} ms")
    return "\n".join(lines)


def _markdown(report: dict[str, object]) -> str:
    measurements = report["measurements"]
    assert isinstance(measurements, dict)
    lines = [
        "# Performance Baseline",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "| Measurement | Min ms | Mean ms | Max ms |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, value in measurements.items():
        assert isinstance(value, dict)
        lines.append(f"| `{name}` | {value['min']} | {value['mean']} | {value['max']} |")
    lines.extend(["", "## Frontend Bundle", ""])
    bundle = report["frontend_bundle"]
    assert isinstance(bundle, dict)
    for name, size in bundle.items():
        lines.append(f"- `{name}`: {size} bytes")
    lines.extend(["", "## Notes", ""])
    notes = report["notes"]
    assert isinstance(notes, list)
    for note in notes:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
