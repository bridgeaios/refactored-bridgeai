"""Pydantic schemas for the twins domain."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DecideRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    twin_id: str = "default"
    context: dict[str, Any] = Field(default_factory=dict)


class DecideResponse(BaseModel):
    ok: bool
    decision: str | None = None
    reasoning: str | None = None
    deterministic: bool = False


class TwinProfile(BaseModel):
    twin_id: str
    name: str | None = None
    status: str = "active"
    capabilities: list[str] = Field(default_factory=list)


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    twin_id: str = "default"
    voice: str | None = None


class EmotionUpdateRequest(BaseModel):
    twin_id: str
    emotion: str
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class CompetitionSubmitRequest(BaseModel):
    twin_id: str
    round_id: str
    answer: str
