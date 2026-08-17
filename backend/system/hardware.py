"""Safe hardware detection with graceful fallbacks."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MemoryInfo(BaseModel):
    total_bytes: int | None = None
    available_bytes: int | None = None


class CpuInfo(BaseModel):
    model: str | None = None
    physical_cores: int | None = None
    logical_processors: int | None = None


class GpuInfo(BaseModel):
    name: str | None = None
    vendor: str | None = None
    vram_total_bytes: int | None = None
    vram_free_bytes: int | None = None
    driver_version: str | None = None
    cuda_driver_version: str | None = None
    compute_capability: str | None = None


class RuntimeAccelerationInfo(BaseModel):
    cuda_available: bool = False
    cuda_driver_version: str | None = None
    cuda_toolkit_available: bool = False
    rocm_available: bool = False
    apple_metal_supported: bool = False


class DiskInfo(BaseModel):
    path: str
    total_bytes: int | None = None
    free_bytes: int | None = None


class HardwareReport(BaseModel):
    operating_system: str
    os_release: str | None = None
    architecture: str
    cpu: CpuInfo
    memory: MemoryInfo
    gpus: list[GpuInfo] = Field(default_factory=list)
    acceleration: RuntimeAccelerationInfo
    disks: list[DiskInfo] = Field(default_factory=list)
    detection_warnings: list[str] = Field(default_factory=list)


def detect_hardware(workspace_path: Path | None = None) -> HardwareReport:
    warnings: list[str] = []
    gpus, acceleration = _detect_gpu(warnings)
    return HardwareReport(
        operating_system=platform.system() or "Unknown",
        os_release=platform.release() or None,
        architecture=platform.machine() or "Unknown",
        cpu=_detect_cpu(warnings),
        memory=_detect_memory(warnings),
        gpus=gpus,
        acceleration=acceleration,
        disks=_detect_disks(workspace_path or Path.cwd(), warnings),
        detection_warnings=warnings,
    )


@lru_cache(maxsize=1)
def cached_hardware_report() -> HardwareReport:
    return detect_hardware()


def clear_hardware_cache() -> None:
    cached_hardware_report.cache_clear()


def _detect_cpu(warnings: list[str]) -> CpuInfo:
    model = platform.processor() or None
    if platform.system() == "Windows":
        model = _windows_cpu_name() or model
    return CpuInfo(
        model=model,
        physical_cores=None,
        logical_processors=os.cpu_count(),
    )


def _windows_cpu_name() -> str | None:
    powershell = _powershell_path()
    if powershell is None:
        return None
    command = (
        "Get-ItemProperty -Path "
        "'HKLM:\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0' | "
        "Select-Object -ExpandProperty ProcessorNameString"
    )
    try:
        completed = subprocess.run(  # noqa: S603
            [
                powershell,
                "-NoProfile",
                "-Command",
                command,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _detect_memory(warnings: list[str]) -> MemoryInfo:
    if platform.system() == "Windows":
        info = _windows_memory()
        if info.total_bytes is not None:
            return info
    if platform.system() == "Linux":
        info = _linux_memory()
        if info.total_bytes is not None:
            return info
    warnings.append("Memory information is partially unavailable.")
    return MemoryInfo()


def _windows_memory() -> MemoryInfo:
    powershell = _powershell_path()
    if powershell is None:
        return MemoryInfo()
    command = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        "$ci = New-Object Microsoft.VisualBasic.Devices.ComputerInfo; "
        '"$($ci.TotalPhysicalMemory),$($ci.AvailablePhysicalMemory)"'
    )
    try:
        completed = subprocess.run(  # noqa: S603
            [
                powershell,
                "-NoProfile",
                "-Command",
                command,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return MemoryInfo()
    if completed.returncode != 0:
        return MemoryInfo()
    parts = [part.strip() for part in completed.stdout.strip().split(",")]
    if len(parts) != 2:
        return MemoryInfo()
    return MemoryInfo(total_bytes=_to_int(parts[0]), available_bytes=_to_int(parts[1]))


def _linux_memory() -> MemoryInfo:
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return MemoryInfo()
    values: dict[str, int] = {}
    for line in lines:
        key, _, raw_value = line.partition(":")
        number = raw_value.strip().split()[0]
        parsed = _to_int(number)
        if parsed is not None:
            values[key] = parsed * 1024
    return MemoryInfo(
        total_bytes=values.get("MemTotal"),
        available_bytes=values.get("MemAvailable"),
    )


def _detect_gpu(warnings: list[str]) -> tuple[list[GpuInfo], RuntimeAccelerationInfo]:
    nvidia_smi = shutil.which("nvidia-smi")
    cuda_toolkit = shutil.which("nvcc") is not None
    rocm_available = shutil.which("rocm-smi") is not None or shutil.which("hipcc") is not None
    metal_supported = platform.system() == "Darwin" and platform.machine() in {"arm64", "aarch64"}
    acceleration = RuntimeAccelerationInfo(
        cuda_toolkit_available=cuda_toolkit,
        rocm_available=rocm_available,
        apple_metal_supported=metal_supported,
    )
    if nvidia_smi is None:
        warnings.append("nvidia-smi was not found.")
        return [], acceleration
    try:
        completed = subprocess.run(  # noqa: S603
            [
                nvidia_smi,
                "--query-gpu=name,driver_version,memory.total,memory.free,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        warnings.append("nvidia-smi detection failed or timed out.")
        return [], acceleration
    if completed.returncode != 0:
        warnings.append("nvidia-smi returned a non-zero exit code.")
        return [], acceleration
    gpus: list[GpuInfo] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            warnings.append("Malformed nvidia-smi GPU row was ignored.")
            continue
        memory_total_mib = _to_int(parts[2])
        memory_free_mib = _to_int(parts[3])
        gpus.append(
            GpuInfo(
                name=parts[0],
                vendor="NVIDIA",
                vram_total_bytes=memory_total_mib * 1024 * 1024 if memory_total_mib else None,
                vram_free_bytes=memory_free_mib * 1024 * 1024 if memory_free_mib else None,
                driver_version=parts[1] or None,
                cuda_driver_version=None,
                compute_capability=parts[4] or None,
            )
        )
    if gpus:
        acceleration.cuda_available = True
    return gpus, acceleration


def _powershell_path() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def _detect_disks(workspace_path: Path, warnings: list[str]) -> list[DiskInfo]:
    try:
        usage = shutil.disk_usage(workspace_path)
    except OSError:
        warnings.append("Disk information is unavailable.")
        return []
    return [
        DiskInfo(
            path=str(workspace_path.resolve().anchor or workspace_path.resolve()),
            total_bytes=usage.total,
            free_bytes=usage.free,
        )
    ]


def _to_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
