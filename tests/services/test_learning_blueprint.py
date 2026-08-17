from __future__ import annotations

from pathlib import Path

from backend.services.learning import LearningService


def test_direct_expert_blueprint_loads_with_expected_tags(tmp_path: Path) -> None:
    service = LearningService(data_dir=tmp_path, workspace_root=Path.cwd())

    blueprint = service.direct_expert_blueprint()

    assert blueprint.id == "direct-expert-ethical-hacking"
    assert blueprint.example_count >= 40
    assert "ethical-hacking" in blueprint.tags
    assert "direct-expert-style" in blueprint.categories
    assert all(
        example.metadata.get("trusted_instructions") is False for example in blueprint.examples
    )


def test_direct_expert_blueprint_import_creates_dataset_version(tmp_path: Path) -> None:
    service = LearningService(data_dir=tmp_path, workspace_root=Path.cwd())

    result = service.import_direct_expert_blueprint()

    assert result.blueprint_id == "direct-expert-ethical-hacking"
    assert result.example_count >= 40
    assert result.imported_count == result.example_count
    assert result.dataset.dataset_id == "direct-expert-ethical-hacking"
    assert result.dataset.train_count > 0
    assert result.dataset.validation_count > 0
    assert result.dataset.test_count > 0
    assert not result.dataset.validation_errors
    assert any("ethical-hacking" in example.tags for example in service.list_examples())
