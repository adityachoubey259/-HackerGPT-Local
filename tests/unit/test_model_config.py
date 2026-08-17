from __future__ import annotations

from pathlib import Path

import pytest

from backend.llm.config import load_model_provider_config
from backend.llm.domain import ProviderType


def test_model_config_loads_defaults_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
default_provider: ollama
providers:
  ollama:
    enabled: true
    type: ollama
    base_url: http://127.0.0.1:11434
""",
        encoding="utf-8",
    )
    config = load_model_provider_config(config_path)
    assert config.default_provider == "ollama"
    assert config.providers["ollama"].type is ProviderType.OLLAMA


def test_model_config_unknown_provider_type_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
providers:
  mystery:
    enabled: true
    type: mystery
    base_url: http://127.0.0.1:9999
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid HackerGPT Local model provider configuration"):
        load_model_provider_config(config_path)


def test_model_config_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
providers:
  ollama:
    enabled: false
    type: ollama
    base_url: http://127.0.0.1:11434
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("HACKERGPT_OLLAMA_ENABLED", "true")
    monkeypatch.setenv("HACKERGPT_OLLAMA_BASE_URL", "http://127.0.0.1:11435")
    config = load_model_provider_config(config_path)
    assert config.providers["ollama"].enabled is True
    assert config.providers["ollama"].base_url == "http://127.0.0.1:11435"
