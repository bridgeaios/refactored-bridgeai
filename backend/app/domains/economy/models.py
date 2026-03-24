"""
Pydantic schemas for the economy domain.

Response models use plain BaseModel so extra fields from legacy services
don't crash serialisation.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in the specified currency")
    currency: str = "BRDG"
    source_project: str = "bridge"
    method: str = "internal"
    type: str = "manual"
    meta: dict[str, Any] = Field(default_factory=dict)


class CollectResponse(BaseModel):
    ok: bool
    tx_id: str | None = None
    splits: dict[str, float] = Field(default_factory=dict)
    message: str | None = None


class TreasuryStatus(BaseModel):
    total: float
    buckets: dict[str, float] = Field(default_factory=dict)
    ledger_size: int = 0
    last_tx: dict[str, Any] | None = None


class UbiClaimRequest(BaseModel):
    address: str = Field(..., min_length=1)


class UbiClaimResponse(BaseModel):
    ok: bool
    amount: float = 0.0
    message: str | None = None


class MarketplaceTask(BaseModel):
    id: int
    title: str
    value: float
    status: str
    posted_by: str | None = None
    claimed_by: str | None = None
    priority_score: float = 0.0


class PostTaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    value: float = Field(..., gt=0)
    tags: list[str] = Field(default_factory=list)
    twin_id: str = "system"
    meta: dict[str, Any] = Field(default_factory=dict)


class AcceptTaskRequest(BaseModel):
    task_id: int
    twin_id: str = Field(..., min_length=1)


class CompleteTaskRequest(BaseModel):
    task_id: int
    twin_id: str = "system"
    result: str | None = None
