from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from backend.system import hardware


def test_hardware_detects_windows_nvidia(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("backend.system.hardware.platform.system", lambda: "Windows")
    monkeypatch.setattr("backend.system.hardware.platform.release", lambda: "11")
    monkeypatch.setattr("backend.system.hardware.platform.machine", lambda: "AMD64")
    monkeypatch.setattr("backend.system.hardware.platform.processor", lambda: "")
    monkeypatch.setattr("backend.system.hardware.os.cpu_count", lambda: 16)
    monkeypatch.setattr(
        "backend.system.hardware.shutil.which",
        lambda name: name if name in {"nvidia-smi", "powershell"} else None,
    )

    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[0] == "nvidia-smi":
            return subprocess.CompletedProcess(args, 0, "RTX 4050, 610.62, 6141, 4500, 8.9\n", "")
        if "CentralProcessor" in args[-1]:
            return subprocess.CompletedProcess(args, 0, "Intel Core\n", "")
        return subprocess.CompletedProcess(args, 0, f"{16 * 1024**3},{8 * 1024**3}\n", "")

    monkeypatch.setattr("backend.system.hardware.subprocess.run", fake_run)
    report = hardware.detect_hardware(tmp_path)
    assert report.cpu.model == "Intel Core"
    assert report.memory.total_bytes == 16 * 1024**3
    assert report.gpus[0].vendor == "NVIDIA"
    assert report.acceleration.cuda_available is True


def test_hardware_handles_missing_nvidia_smi(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("backend.system.hardware.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.system.hardware.platform.release", lambda: "6")
    monkeypatch.setattr("backend.system.hardware.platform.machine", lambda: "x86_64")
    monkeypatch.setattr("backend.system.hardware.platform.processor", lambda: "CPU")
    monkeypatch.setattr("backend.system.hardware.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "backend.system.hardware._linux_memory",
        lambda: hardware.MemoryInfo(total_bytes=8, available_bytes=4),
    )
    report = hardware.detect_hardware(tmp_path)
    assert report.gpus == []
    assert report.acceleration.cuda_available is False
    assert "nvidia-smi was not found." in report.detection_warnings


def test_hardware_handles_malformed_gpu_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("backend.system.hardware.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.system.hardware.platform.release", lambda: "6")
    monkeypatch.setattr("backend.system.hardware.platform.machine", lambda: "x86_64")
    monkeypatch.setattr("backend.system.hardware.platform.processor", lambda: "CPU")
    monkeypatch.setattr(
        "backend.system.hardware.shutil.which",
        lambda name: "nvidia-smi" if name == "nvidia-smi" else None,
    )
    monkeypatch.setattr(
        "backend.system.hardware.subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "bad,row\n", ""),
    )
    monkeypatch.setattr(
        "backend.system.hardware._linux_memory",
        lambda: hardware.MemoryInfo(total_bytes=8, available_bytes=4),
    )
    report = hardware.detect_hardware(tmp_path)
    assert report.gpus == []
    assert "Malformed nvidia-smi GPU row was ignored." in report.detection_warnings


def test_hardware_handles_detector_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("backend.system.hardware.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.system.hardware.platform.release", lambda: "6")
    monkeypatch.setattr("backend.system.hardware.platform.machine", lambda: "x86_64")
    monkeypatch.setattr("backend.system.hardware.platform.processor", lambda: "CPU")
    monkeypatch.setattr(
        "backend.system.hardware.shutil.which",
        lambda name: "nvidia-smi" if name == "nvidia-smi" else None,
    )

    def fake_run(_args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("nvidia-smi", 3)

    monkeypatch.setattr("backend.system.hardware.subprocess.run", fake_run)
    monkeypatch.setattr(
        "backend.system.hardware._linux_memory",
        lambda: hardware.MemoryInfo(total_bytes=8, available_bytes=4),
    )
    report = hardware.detect_hardware(tmp_path)
    assert report.gpus == []
    assert "nvidia-smi detection failed or timed out." in report.detection_warnings


def test_hardware_marks_apple_metal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("backend.system.hardware.platform.system", lambda: "Darwin")
    monkeypatch.setattr("backend.system.hardware.platform.release", lambda: "15")
    monkeypatch.setattr("backend.system.hardware.platform.machine", lambda: "arm64")
    monkeypatch.setattr("backend.system.hardware.platform.processor", lambda: "Apple")
    monkeypatch.setattr("backend.system.hardware.shutil.which", lambda _name: None)
    report = hardware.detect_hardware(tmp_path)
    assert report.acceleration.apple_metal_supported is True
