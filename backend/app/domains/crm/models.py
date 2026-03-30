"""Pydantic schemas for the CRM domain."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class OsintProfile(BaseModel):
    company_name: str = ""
    industry: str = "unknown"
    size_estimate: str = "unknown"
    email_domain: str = ""
    decision_makers: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    template_type: str = "generic"
    profile_confidence: float = 0.0


class LeadIngest(BaseModel):
    """Payload workers.py sends to POST /api/crm/leads."""
    email: str
    company: str = ""
    name: str = ""
    phone: str = ""
    source: str = "scraper"
    osint_profile: OsintProfile | dict[str, Any] = Field(default_factory=dict)


class LeadResponse(BaseModel):
    ok: bool
    id: str
    email: str
    company: str
    stage: str
    score: float
    duplicate: bool = False


class LeadDetail(BaseModel):
    id: str
    email: str
    company: str
    name: str
    phone: str
    source: str
    stage: str
    score: float
    industry: str
    size_estimate: str
    pain_points: list[str]
    template_type: str
    created_at: str
    updated_at: str
    activities: list[dict[str, Any]] = Field(default_factory=list)


class StageUpdate(BaseModel):
    stage: str = Field(..., pattern="^(new|qualified|proposal|negotiation|won|lost)$")
    note: str = ""


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class DealCreate(BaseModel):
    lead_id: str
    title: str
    value: float = Field(0.0, ge=0)
    currency: str = "ZAR"


class DealResponse(BaseModel):
    ok: bool
    id: str
    lead_id: str
    title: str
    value: float
    currency: str
    stage: str


class PipelineStage(BaseModel):
    name: str
    count: int
    total_value: float


class PipelineResponse(BaseModel):
    stages: list[PipelineStage]
    total_leads: int
    total_value: float


class CrmStats(BaseModel):
    total_leads: int
    by_stage: dict[str, int]
    by_source: dict[str, int]
    by_industry: dict[str, int]
    avg_score: float
    conversion_rate: float
