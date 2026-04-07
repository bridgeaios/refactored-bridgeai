"""Pydantic schemas for the Compliance domain."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DOC_TYPES = Literal[
    "nda", "msa", "privacy_policy", "terms_of_service",
    "sla", "data_processing", "gdpr_consent", "other"
]


class ComplianceDoc(BaseModel):
    id: str
    name: str
    doc_type: str
    filename: str
    size_bytes: int
    uploaded_at: str
    uploader: str = ""
    contact_id: str = ""   # linked CRM lead/contact if any
    notes: str = ""


class DocUploadMeta(BaseModel):
    doc_type: str = "other"
    notes: str = ""
    contact_id: str = ""


class AISuggestionRequest(BaseModel):
    contact_id: str = ""
    context: str = Field("", max_length=500)
