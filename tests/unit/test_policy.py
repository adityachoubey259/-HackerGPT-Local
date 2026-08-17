from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.policy import AccessMode, ResponseMode, load_policy
from backend.services.prompts import compose_system_prompt


def test_policy_yaml_loads() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    assert policy.privacy.local_first is True
    assert policy.network_access.cloud_inference is AccessMode.DISABLED
    assert policy.privacy.retrieved_content_is_untrusted is True
    assert policy.effective_response.default_mode is ResponseMode.DIRECT_EXPERT
    assert policy.effective_response.shallow_keyword_filtering is False


def test_legacy_response_behavior_key_still_loads(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
response_behavior:
  default_mode: standard
  cite_retrieved_sources: false
""",
        encoding="utf-8",
    )
    policy = load_policy(policy_path)
    assert policy.effective_response.default_mode is ResponseMode.STANDARD
    assert policy.effective_response.cite_retrieved_sources is False


def test_direct_expert_prompt_composition_preserves_boundaries() -> None:
    prompt = compose_system_prompt("Base app prompt.", load_policy(Path("config/policy.yaml")))
    assert "RESPONSE MODE: Direct Expert" in prompt
    assert "ToolRegistry" in prompt
    assert "PermissionService" in prompt
    assert "Do not execute commands" in prompt
    assert "Do not use shallow keyword-based filtering" in prompt
    assert "If only one portion crosses a hard application boundary" in prompt
    assert "Investigate before declaring unknown" in prompt
    assert "Never fabricate APIs" in prompt


def test_invalid_policy_fails(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
network_access:
  cloud_inference: enabled
model_routing:
  cloud_fallback_enabled: false
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid HackerGPT Local policy configuration"):
        load_policy(policy_path)


def test_invalid_command_permission_fails(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
command_execution:
  default_permission: ROOT
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid HackerGPT Local policy configuration"):
        load_policy(policy_path)
