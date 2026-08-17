from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.config import AppSettings, load_settings


def test_settings_defaults_are_local_first(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.yaml")
    assert settings.environment == "development"
    assert settings.network_access is False
    assert settings.model_endpoint.cloud_inference_enabled is False
    assert settings.database.url.startswith("sqlite+aiosqlite:///")


def test_yaml_loading(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
environment: test
api:
  port: 9001
logging:
  level: debug
""",
        encoding="utf-8",
    )
    settings = load_settings(config_path)
    assert settings.environment == "test"
    assert settings.api.port == 9001
    assert settings.logging.level == "DEBUG"


def test_environment_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("api:\n  port: 9001\n", encoding="utf-8")
    monkeypatch.setenv("HACKERGPT_API_PORT", "8123")
    monkeypatch.setenv("HACKERGPT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    settings = load_settings(config_path)
    assert settings.api.port == 8123
    assert settings.api.allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_invalid_config_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("environment: staging\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid HackerGPT Local configuration"):
        load_settings(config_path)


def test_public_config_excludes_secret() -> None:
    settings = AppSettings(
        model_endpoint={"base_url": "http://localhost:11434", "api_key": "secret-token"}
    )
    public = settings.public_config()
    assert "api_key" not in str(public)
    assert "secret-token" not in str(public)
