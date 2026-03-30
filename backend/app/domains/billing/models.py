"""Pydantic schemas for the billing/invoicing domain."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str = Field(..., min_length=1)
    quantity: float = Field(1.0, gt=0)
    unit_price: float = Field(..., gt=0)

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class InvoiceCreate(BaseModel):
    lead_id: str | None = None
    deal_id: str | None = None
    client_email: str
    client_name: str = ""
    client_company: str = ""
    items: list[InvoiceLineItem] = Field(..., min_length=1)
    currency: str = "ZAR"
    tax_rate: float = Field(0.15, ge=0, le=1)  # 15% VAT default
    due_days: int = Field(30, ge=0, le=365)
    notes: str = ""


class InvoiceResponse(BaseModel):
    ok: bool
    id: str
    invoice_number: str
    status: str
    subtotal: float
    tax: float
    total: float
    currency: str
    due_date: str


class InvoiceDetail(BaseModel):
    id: str
    invoice_number: str
    client_email: str
    client_name: str
    client_company: str
    lead_id: str | None
    deal_id: str | None
    items: list[dict[str, Any]]
    subtotal: float
    tax_rate: float
    tax: float
    total: float
    currency: str
    status: str
    notes: str
    issued_at: str
    due_date: str
    paid_at: str | None
    payment_method: str | None


class MarkPaidRequest(BaseModel):
    payment_method: str = "manual"
    reference: str = ""
