from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DecideRequest(BaseModel):
    environment: dict[str, Any] = Field(default_factory=dict)
    goal_vector: list[float] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risk_threshold: float = 0.5
    candidates: list[Any] = Field(default_factory=list)


class TwinProfile(BaseModel):
    twin_id: str
    name: Optional[str] = None
    status: str = "active"
    capabilities: list[str] = Field(default_factory=list)


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    twin_id: str = "default"
    voice: Optional[str] = None


class EmotionUpdateRequest(BaseModel):
    twin_id: str
    emotion: str
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class CompetitionSubmitRequest(BaseModel):
    twin_id: str
    round_id: str
    answer: str
