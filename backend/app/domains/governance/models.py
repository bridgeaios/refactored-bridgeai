"""Pydantic schemas for the governance domain."""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class GovernanceProposalRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    proposer_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GovernanceVoteRequest(BaseModel):
    proposal_id: str
    voter_id: str
    vote: str  # "yes" | "no" | "abstain"


class ReputationQuery(BaseModel):
    agent_id: str


class MissionUpdateRequest(BaseModel):
    title: str
    status: str = "active"
    payload: dict[str, Any] = Field(default_factory=dict)


class KnowledgeNodeRequest(BaseModel):
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
