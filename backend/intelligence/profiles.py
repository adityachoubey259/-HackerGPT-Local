"""Config-backed model profile registry."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import yaml

from backend.intelligence.models import ModelCapabilityProfile


class ModelProfileRegistry:
    def __init__(self, config_dir: Path = Path("config/model-profiles")) -> None:
        self._config_dir = config_dir
        self._profiles: list[ModelCapabilityProfile] = []
        self.reload()

    def reload(self) -> None:
        profiles: list[ModelCapabilityProfile] = []
        if self._config_dir.exists():
            for path in sorted(self._config_dir.glob("*.yaml")):
                loaded = _read_yaml(path)
                records = loaded if isinstance(loaded, list) else loaded.get("profiles", [])
                if not isinstance(records, list):
                    continue
                for record in records:
                    if isinstance(record, dict):
                        profiles.append(ModelCapabilityProfile.model_validate(record))
        self._profiles = profiles

    def list(self) -> list[ModelCapabilityProfile]:
        return list(self._profiles)

    def match(self, model_name: str) -> ModelCapabilityProfile | None:
        normalized = model_name.lower()
        for profile in self._profiles:
            if fnmatch.fnmatch(normalized, profile.pattern.lower()):
                return profile
        return None


def _read_yaml(path: Path) -> dict[str, Any] | list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded: Any = yaml.safe_load(handle) or {}
    if not isinstance(loaded, (dict, list)):
        return {}
    return loaded
