"""Training backend interface and optional Transformers/PEFT backend."""

from __future__ import annotations

import importlib.util
import shutil
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from backend.system.hardware import HardwareReport
from backend.training.models import (
    TrainingBackendCapabilities,
    TrainingFit,
    TrainingPreflightRequest,
    TrainingPreflightResult,
)
from backend.training.presets import preset_config


class BaseTrainingBackend(Protocol):
    backend_id: str

    def capabilities(self) -> TrainingBackendCapabilities: ...

    def preflight(
        self,
        request: TrainingPreflightRequest,
        *,
        hardware: HardwareReport,
        dataset: dict[str, object],
        workspace_root: Path,
    ) -> TrainingPreflightResult: ...


class TransformersPeftTrainingBackend:
    backend_id = "transformers-peft"

    def capabilities(self) -> TrainingBackendCapabilities:
        installed = all(
            importlib.util.find_spec(package) is not None
            for package in ("transformers", "peft", "datasets", "accelerate", "torch")
        )
        return TrainingBackendCapabilities(
            backend_id=self.backend_id,
            label="Transformers + PEFT LoRA",
            supported_model_families=[
                "small causal language models supported by Hugging Face Transformers",
            ],
            adapter_types=["lora"],
            quantized_training_available=False,
            gpu_required=False,
            cpu_compatible=True,
            checkpoint_support=True,
            resume_support=True,
            cancellation_support=True,
            installed=installed,
            install_hint=None if installed else 'Install with: pip install -e ".[training]"',
        )

    def preflight(
        self,
        request: TrainingPreflightRequest,
        *,
        hardware: HardwareReport,
        dataset: dict[str, object],
        workspace_root: Path,
    ) -> TrainingPreflightResult:
        capabilities = self.capabilities()
        reasons: list[str] = []
        warnings: list[str] = []
        fit = TrainingFit.POSSIBLE
        preset = preset_config(request.preset, sequence_length=request.sequence_length)
        example_count = _int(dataset.get("example_count"))
        validation_errors = _str_list(dataset.get("validation_errors"))
        if not capabilities.installed:
            fit = TrainingFit.UNSUPPORTED
            reasons.append("Optional training dependencies are not installed.")
        if request.adapter_type != "lora":
            fit = TrainingFit.UNSUPPORTED
            reasons.append("Only LoRA adapters are supported by the initial backend.")
        if request.quantized and not capabilities.quantized_training_available:
            fit = TrainingFit.UNSUPPORTED
            reasons.append("Quantized training requires optional bitsandbytes support.")
        if validation_errors:
            fit = TrainingFit.UNSUPPORTED
            reasons.extend(validation_errors)
        if example_count == 0:
            fit = TrainingFit.UNSUPPORTED
            reasons.append("Dataset has no examples.")
        if example_count and example_count < 8:
            warnings.append("Dataset is tiny; this is suitable only for architecture smoke tests.")
        if not Path(request.base_model).expanduser().exists():
            warnings.append(
                "Base model path was not found locally; the worker uses local_files_only and will "
                "not download model weights automatically."
            )
        largest_vram = max((gpu.vram_total_bytes or 0 for gpu in hardware.gpus), default=0)
        available_ram = hardware.memory.available_bytes or hardware.memory.total_bytes or 0
        if fit != TrainingFit.UNSUPPORTED:
            if largest_vram >= 8 * 1024**3:
                fit = TrainingFit.RECOMMENDED
                reasons.append("GPU VRAM appears suitable for small LoRA experiments.")
            elif largest_vram >= 4 * 1024**3:
                fit = TrainingFit.POSSIBLE
                reasons.append("GPU VRAM appears suitable for tiny LoRA smoke tests.")
            elif available_ram >= 12 * 1024**3:
                fit = TrainingFit.SLOW
                reasons.append("CPU training may run but is expected to be slow.")
            else:
                fit = TrainingFit.UNLIKELY_TO_FIT
                reasons.append("Available RAM/VRAM is low for local adapter training.")
        disk = hardware.disks[0] if hardware.disks else None
        if disk and disk.free_bytes is not None and disk.free_bytes < 5 * 1024**3:
            warnings.append("Less than 5 GiB free disk space is available.")
        torch_status = _torch_status()
        return TrainingPreflightResult(
            backend=capabilities,
            fit=fit,
            reasons=reasons or ["Preflight completed."],
            warnings=warnings,
            hardware={
                "operating_system": hardware.operating_system,
                "architecture": hardware.architecture,
                "cpu": hardware.cpu.model,
                "logical_processors": hardware.cpu.logical_processors,
                "memory_total_bytes": hardware.memory.total_bytes,
                "memory_available_bytes": hardware.memory.available_bytes,
                "gpu_count": len(hardware.gpus),
                "largest_vram_bytes": largest_vram or None,
                "cuda_driver_marker": hardware.acceleration.cuda_available,
                "cuda_toolkit_available": hardware.acceleration.cuda_toolkit_available,
                "torch": torch_status,
                "workspace": str(workspace_root),
            },
            dataset=dataset,
            preset=preset,
        )


def training_backends() -> list[BaseTrainingBackend]:
    return [TransformersPeftTrainingBackend()]


def get_training_backend(backend_id: str) -> BaseTrainingBackend:
    for backend in training_backends():
        if backend.backend_id == backend_id:
            return backend
    msg = f"Unknown training backend: {backend_id}"
    raise ValueError(msg)


def _torch_status() -> dict[str, object]:
    if importlib.util.find_spec("torch") is None:
        return {"installed": False, "cuda_available": False}
    torch = cast(Any, import_module("torch"))

    cuda_available = bool(torch.cuda.is_available())
    return {
        "installed": True,
        "version": str(getattr(torch, "__version__", "unknown")),
        "cuda_available": cuda_available,
        "cuda_device_count": int(torch.cuda.device_count()) if cuda_available else 0,
        "cuda_device_name": str(torch.cuda.get_device_name(0)) if cuda_available else None,
        "nvcc_available": shutil.which("nvcc") is not None,
    }


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
