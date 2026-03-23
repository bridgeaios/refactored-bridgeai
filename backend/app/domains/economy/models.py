"""
Pydantic schemas for the economy domain.

Response models use plain BaseModel so extra fields from legacy services
don't crash serialisation.
"""
from __future__ import annotations

from typing import Any, Optional

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
    tx_id: Optional[str] = None
    splits: dict[str, float] = Field(default_factory=dict)
    message: Optional[str] = None


class TreasuryStatus(BaseModel):
    total: float
    buckets: dict[str, float] = Field(default_factory=dict)
    ledger_size: int = 0
    last_tx: Optional[dict[str, Any]] = None


class UbiClaimRequest(BaseModel):
    address: str = Field(..., min_length=1)


class UbiClaimResponse(BaseModel):
    ok: bool
    amount: float = 0.0
    message: Optional[str] = None


class MarketplaceTask(BaseModel):
    id: int
    title: str
    value: float
    status: str
    posted_by: Optional[str] = None
    claimed_by: Optional[str] = None
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
    result: Optional[str] = None
