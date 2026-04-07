"""Pydantic models for bridgeos.tvm."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TVMPrincipal(BaseModel):
    name: str
    roles: list[str] = Field(default_factory=list)


class TVMRow(BaseModel):
    topic: str
    configured: int = 0
    healthy: int = 0
    degraded: int = 0
    action_required: int = 0
    autofix_available: int = 0
    human_approval_needed: int = 0
    last_updated: int = 0
    recommendation_code: Optional[str] = None
    signature: Optional[str] = None


class TVMProposalBody(BaseModel):
    recommendation_code: str


class TVMApprovalBody(BaseModel):
    approve: bool = True


class ExecutorResultBody(BaseModel):
    """Inbound executor.result shape (TVM consumes and updates row)."""

    recommendation_code: str
    status: str  # success | partial | failed
    details: str = ""
    new_health: int = 0
    new_degraded: int = 0
    correlation_id: str = ""
    emitted_at: Optional[int] = None


class TVMEventEnvelope(BaseModel):
    """Generic envelope for in-process event bus (stub)."""

    event_type: str
    version: str = "1.0"
    topic: Optional[str] = None
    correlation_id: str = ""
    emitted_at: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
