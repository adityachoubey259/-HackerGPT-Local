"""Prompt profile loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.prompting.models import PromptProfile, PromptType


class PromptProfileRegistry:
    def __init__(self, config_dir: Path = Path("config/prompt-profiles")) -> None:
        self._config_dir = config_dir
        self._profiles: list[PromptProfile] = []
        self.reload()

    def reload(self) -> None:
        profiles: list[PromptProfile] = []
        if self._config_dir.exists():
            for path in sorted(self._config_dir.glob("*.yaml")):
                loaded = _read_yaml(path)
                records = loaded.get("profiles", []) if isinstance(loaded, dict) else []
                if isinstance(records, list):
                    for record in records:
                        if isinstance(record, dict):
                            profiles.append(PromptProfile.model_validate(record))
        self._profiles = profiles

    def list(self) -> list[PromptProfile]:
        return list(self._profiles)

    def match(self, prompt_type: PromptType, language: str | None) -> PromptProfile | None:
        language_normalized = (language or "").lower()
        candidates = [profile for profile in self._profiles if profile.prompt_type == prompt_type]
        if language_normalized:
            for profile in candidates:
                if language_normalized in {item.lower() for item in profile.languages}:
                    return profile
        return candidates[0] if candidates else None


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded: Any = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}
