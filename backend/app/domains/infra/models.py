"""Pydantic schemas for the infra domain."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool = True
    status: str = "ok"
    service: str = "bridge-api"


class SiweLoginRequest(BaseModel):
    message: str
    signature: str


class SiweLoginResponse(BaseModel):
    ok: bool
    token: str | None = None
    message: str | None = None


class CliCommandRequest(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class TelemetrySnapshot(BaseModel):
    timestamp: float
    metrics: dict[str, Any] = Field(default_factory=dict)


class MemoryGetRequest(BaseModel):
    key: str


class MemorySetRequest(BaseModel):
    key: str
    value: Any
    ttl: int | None = None
