"""Billing domain router — invoice lifecycle."""
from __future__ import annotations

from typing import Annotated, Any

import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

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
    """Mark invoice as sent and email it to the client."""
    invoice = await svc.mark_sent(invoice_id)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")

    email_queued = False
    try:
        import os, html as _html
        from app.services.email_sender import send_email
        provider = os.environ.get("OUTREACH_EMAIL_PROVIDER", "")
        if provider:
            client_email = invoice.get("client_email", "")
            client_name = invoice.get("client_name") or invoice.get("client_company") or "Client"
            inv_number = invoice.get("invoice_number", invoice_id)
            total = invoice.get("total", 0)
            currency = invoice.get("currency", "ZAR")
            due_date = invoice.get("due_date", "—")
            pay_link = invoice.get("payment_link") or ""
            pay_section = (
                f'<p style="margin:1rem 0"><a href="{_html.escape(pay_link)}" '
                f'style="background:#0284c7;color:#fff;padding:.6rem 1.4rem;border-radius:6px;'
                f'text-decoration:none;font-weight:600">Pay Now</a></p>'
                if pay_link else ""
            )
            subject = f"Invoice {inv_number} from BridgeAI — {currency} {total:,.2f} due {due_date}"
            html_body = f"""
<div style="font-family:Inter,system-ui,sans-serif;max-width:560px;margin:0 auto;color:#1e293b">
  <div style="background:#0f172a;padding:1.5rem 2rem;border-radius:8px 8px 0 0">
    <h2 style="color:#38bdf8;margin:0;font-size:1.1rem">BridgeAI Invoice</h2>
  </div>
  <div style="background:#f8fafc;padding:1.5rem 2rem;border-radius:0 0 8px 8px;border:1px solid #e2e8f0">
    <p>Hi {_html.escape(client_name)},</p>
    <p>Please find your invoice <strong>{_html.escape(inv_number)}</strong> attached.</p>
    <table style="width:100%;border-collapse:collapse;margin:1rem 0">
      <tr><td style="padding:.4rem 0;color:#64748b">Amount due</td>
          <td style="text-align:right;font-weight:700">{currency} {total:,.2f}</td></tr>
      <tr><td style="padding:.4rem 0;color:#64748b">Due date</td>
          <td style="text-align:right">{_html.escape(due_date)}</td></tr>
    </table>
    {pay_section}
    <p style="color:#64748b;font-size:.85rem">Questions? Reply to this email.</p>
  </div>
</div>"""
            text_body = (
                f"Hi {client_name},\n\nInvoice {inv_number} — {currency} {total:,.2f} due {due_date}.\n"
                + (f"\nPay online: {pay_link}\n" if pay_link else "")
                + "\nThank you,\nBridgeAI"
            )
            result = await send_email(client_email, subject, html_body, text_body)
            email_queued = result.get("ok", False)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Invoice email failed for %s", invoice_id)

    return {"ok": True, "invoice": invoice, "email_queued": email_queued}


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


@router.get("/invoices/{invoice_id}/payment-link")
async def get_payment_link(
    invoice_id: str, svc: BillingDep, _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    """Return cached Paystack payment link; regenerates if absent (e.g. key added post-creation)."""
    invoice = await svc.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")
    link = invoice.get("payment_link")
    if not link:
        link = await svc._paystack_link(invoice)
        if link:
            invoice["payment_link"] = link
            from app.core.deps import get_memory
            await get_memory().set(f"billing:invoice:{invoice_id}", invoice)
    return {"ok": True, "payment_link": link, "invoice_number": invoice.get("invoice_number")}


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    svc: BillingDep,
    _: dict = Depends(require_jwt),
) -> Response:
    """Stream invoice as a branded PDF."""
    invoice = await svc.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")
    try:
        from app.services.pdf_generator import generate_invoice_pdf
        pdf_bytes = generate_invoice_pdf(invoice)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("PDF generation failed for %s", invoice_id)
        raise HTTPException(500, detail="PDF generation failed") from exc
    filename = f"{invoice.get('invoice_number', invoice_id)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/invoices/reconcile")
async def reconcile_webhook(
    request: Request,
    svc: BillingDep,
) -> dict[str, Any]:
    """Called by Paystack payment webhooks to auto-match and mark invoices paid.

    Verifies the Paystack HMAC-SHA512 signature before processing.
    No JWT required — this endpoint is called by Paystack, not by users.
    """
    secret = os.environ.get("PAYSTACK_SECRET_KEY", "")
    if not secret:
        raise HTTPException(500, detail="Payment webhook secret not configured")

    signature = request.headers.get("x-paystack-signature", "")
    body = await request.body()

    expected = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, detail="Invalid webhook signature")

    import json as _json
    payload = _json.loads(body)
    data = payload.get("data", payload)
    amount = float(data.get("amount", 0)) / 100  # Paystack amounts are in kobo
    currency = str(data.get("currency", "ZAR"))
    method = "paystack"
    invoice = await svc.reconcile_by_amount(amount, currency, method)
    return {"ok": True, "matched": invoice is not None, "invoice": invoice}
