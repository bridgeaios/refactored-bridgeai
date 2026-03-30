"""Billing domain router — invoice lifecycle."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.billing.deps import get_billing
from app.domains.billing.models import InvoiceCreate, MarkPaidRequest
from app.domains.billing.services import BillingService
from app.domains.infra.deps import require_jwt

router = APIRouter(tags=["billing"])

BillingDep = Annotated[BillingService, Depends(get_billing)]


@router.post("/invoices")
async def create_invoice(
    payload: InvoiceCreate,
    svc: BillingDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    invoice = await svc.create_invoice(payload.model_dump())
    return {"ok": True, "invoice": invoice}


@router.get("/invoices")
async def list_invoices(
    svc: BillingDep,
    _: dict = Depends(require_jwt),
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    invoices = await svc.list_invoices(status=status, limit=limit, offset=offset)
    return {"ok": True, "invoices": invoices, "count": len(invoices)}


@router.get("/invoices/stats")
async def invoice_stats(svc: BillingDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.stats()


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, svc: BillingDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    invoice = await svc.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: str, svc: BillingDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Mark invoice as sent. Wire email delivery via OUTREACH_EMAIL_PROVIDER."""
    invoice = await svc.mark_sent(invoice_id)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")
    # TODO: trigger email via outreach domain when OUTREACH_EMAIL_PROVIDER is set
    return {"ok": True, "invoice": invoice, "email_queued": False}


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_paid(
    invoice_id: str,
    payload: MarkPaidRequest,
    svc: BillingDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    invoice = await svc.mark_paid(invoice_id, payload.payment_method, payload.reference)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")
    return {"ok": True, "invoice": invoice}


@router.post("/invoices/flag-overdue")
async def flag_overdue(svc: BillingDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    count = await svc.flag_overdue()
    return {"ok": True, "updated": count}


@router.post("/invoices/reconcile")
async def reconcile_webhook(
    payload: dict[str, Any],
    svc: BillingDep,
) -> dict[str, Any]:
    """Called by payment webhooks to auto-match and mark invoices paid."""
    amount = float(payload.get("amount", 0))
    currency = str(payload.get("currency", "ZAR"))
    method = str(payload.get("method", "webhook"))
    invoice = await svc.reconcile_by_amount(amount, currency, method)
    return {"ok": True, "matched": invoice is not None, "invoice": invoice}
