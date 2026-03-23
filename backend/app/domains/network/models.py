"""Pydantic schemas for the network domain."""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class NodeRegisterRequest(BaseModel):
    node_id: str = Field(..., min_length=1)
    url: str
    capabilities: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class SwarmMessageRequest(BaseModel):
    channel: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sender_id: str = "system"


class ProjectRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    url: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ReplicationSyncRequest(BaseModel):
    target_node: str
    data: dict[str, Any] = Field(default_factory=dict)
