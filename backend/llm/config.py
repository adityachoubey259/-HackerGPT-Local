"""Model provider configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from backend.llm.domain import ModelProviderConfiguration

DEFAULT_MODELS_CONFIG_PATH = Path("config/models.yaml")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        msg = f"Model config at {path} must contain a mapping"
        raise ValueError(msg)
    return loaded


def _apply_env(data: dict[str, Any]) -> dict[str, Any]:
    providers = data.setdefault("providers", {})
    env_mappings = {
        "ollama": {
            "enabled": "HACKERGPT_OLLAMA_ENABLED",
            "base_url": "HACKERGPT_OLLAMA_BASE_URL",
        },
        "llama_cpp": {
            "enabled": "HACKERGPT_LLAMA_CPP_ENABLED",
            "base_url": "HACKERGPT_LLAMA_CPP_BASE_URL",
        },
        "openai_compatible": {
            "enabled": "HACKERGPT_OPENAI_COMPATIBLE_ENABLED",
            "base_url": "HACKERGPT_OPENAI_COMPATIBLE_BASE_URL",
            "api_key": "HACKERGPT_OPENAI_COMPATIBLE_API_KEY",
        },
        "vllm": {
            "enabled": "HACKERGPT_VLLM_ENABLED",
            "base_url": "HACKERGPT_VLLM_BASE_URL",
            "api_key": "HACKERGPT_VLLM_API_KEY",
        },
    }
    for provider_id, mapping in env_mappings.items():
        if not any(env_key in os.environ for env_key in mapping.values()):
            continue
        provider = providers.setdefault(provider_id, {})
        for config_key, env_key in mapping.items():
            if env_key in os.environ:
                value: str | bool = os.environ[env_key]
                if config_key == "enabled":
                    value = os.environ[env_key].lower() in {"1", "true", "yes", "on"}
                provider[config_key] = value
    if "HACKERGPT_DEFAULT_PROVIDER" in os.environ:
        data["default_provider"] = os.environ["HACKERGPT_DEFAULT_PROVIDER"]
    if "HACKERGPT_DEFAULT_MODEL" in os.environ:
        data["default_model"] = os.environ["HACKERGPT_DEFAULT_MODEL"]
    return data


def load_model_provider_config(
    path: Path | None = None,
) -> ModelProviderConfiguration:
    config_path = path or Path(
        os.getenv("HACKERGPT_MODELS_CONFIG_FILE", str(DEFAULT_MODELS_CONFIG_PATH))
    )
    data = _apply_env(_load_yaml(config_path))
    try:
        return ModelProviderConfiguration.model_validate(data)
    except ValidationError as exc:
        msg = "Invalid HackerGPT Local model provider configuration"
        raise ValueError(msg) from exc
