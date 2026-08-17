"""Transparent local training presets."""

from __future__ import annotations

from backend.training.models import TrainingPreset, TrainingPresetConfig

PRESETS: dict[TrainingPreset, TrainingPresetConfig] = {
    TrainingPreset.QUICK: TrainingPresetConfig(
        preset=TrainingPreset.QUICK,
        epochs=0.03,
        max_steps=3,
        learning_rate=2e-4,
        batch_size=1,
        gradient_accumulation_steps=1,
        sequence_length=128,
        lora_rank=4,
        lora_alpha=8,
        lora_dropout=0.05,
        validation_split=0.25,
    ),
    TrainingPreset.BALANCED: TrainingPresetConfig(
        preset=TrainingPreset.BALANCED,
        epochs=1,
        max_steps=80,
        learning_rate=1e-4,
        batch_size=1,
        gradient_accumulation_steps=4,
        sequence_length=512,
        lora_rank=8,
        lora_alpha=16,
        lora_dropout=0.05,
        validation_split=0.2,
    ),
    TrainingPreset.QUALITY: TrainingPresetConfig(
        preset=TrainingPreset.QUALITY,
        epochs=2,
        max_steps=240,
        learning_rate=8e-5,
        batch_size=1,
        gradient_accumulation_steps=8,
        sequence_length=1024,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        validation_split=0.2,
    ),
}


def preset_config(
    preset: TrainingPreset,
    *,
    sequence_length: int | None = None,
) -> TrainingPresetConfig:
    config = PRESETS.get(preset, PRESETS[TrainingPreset.QUICK])
    if sequence_length is None:
        return config
    return config.model_copy(update={"sequence_length": sequence_length})
