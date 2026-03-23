"""
Shared Pydantic base models and response envelopes used across all domains.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BridgeBaseModel(BaseModel):
    """
    Base model for all Bridge AI OS request/response schemas.
    - Forbids extra fields (no silent data loss).
    - Immutable after construction.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)


class OkResponse(BaseModel):
    """Standard success envelope."""
    ok: bool = True
    data: Any = None


class ErrorResponse(BaseModel):
    """Standard error envelope — mirrors error_response() in core/errors.py."""
    ok: bool = False
    code: str
    message: str
