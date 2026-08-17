"""User preference API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.core.policy import ResponseMode, TechnicalDepth


class UserPreferencesResponse(BaseModel):
    response_mode: ResponseMode
    technical_depth: TechnicalDepth
    default_agent: str | None = Field(default=None, max_length=80)
    intelligence_mode: Literal["auto", "speed", "quality", "local_only"] = "auto"
    reasoning_mode: Literal["auto", "fast", "deep"] = "auto"
    theme: Literal["system", "light", "dark"] = "system"


class UserPreferencesPatch(BaseModel):
    response_mode: ResponseMode | None = None
    technical_depth: TechnicalDepth | None = None
    default_agent: str | None = Field(default=None, max_length=80)
    intelligence_mode: Literal["auto", "speed", "quality", "local_only"] | None = None
    reasoning_mode: Literal["auto", "fast", "deep"] | None = None
    theme: Literal["system", "light", "dark"] | None = None
