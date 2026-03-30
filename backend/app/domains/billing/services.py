"""Billing domain service — invoice lifecycle management."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

log = logging.getLogger(__name__)

INVOICE_STATUSES = ("draft", "sent", "paid", "overdue", "cancelled")


class BillingService:
    """Invoice management backed by Redis/MemoryStore.
    Production: migrate to PostgreSQL with SQLAlchemy (same DATABASE_DEFI_URL pattern).
    """

    def __init__(self, memory: MemoryStore) -> None:
        self._mem = memory

    # ------------------------------------------------------------------
    # Invoice number sequencing
    # ------------------------------------------------------------------

    async def _next_invoice_number(self) -> str:
        year = datetime.utcnow().year
        seq_key = f"billing:seq:{year}"
        seq: int = await self._mem.get(seq_key) or 0
        seq += 1
        await self._mem.set(seq_key, seq)
        return f"INV-{year}-{seq:04d}"

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow()
        due_days = int(payload.get("due_days", 30))
        due_date = (now + timedelta(days=due_days)).strftime("%Y-%m-%d")

        items = payload.get("items", [])
        subtotal = round(sum(
            float(i.get("quantity", 1)) * float(i.get("unit_price", 0))
            for i in items
        ), 2)
        tax_rate = float(payload.get("tax_rate", 0.15))
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

        invoice_number = await self._next_invoice_number()
        invoice_id = str(uuid4())

        invoice: dict[str, Any] = {
            "id": invoice_id,
            "invoice_number": invoice_number,
            "client_email": payload.get("client_email", ""),
            "client_name": payload.get("client_name", ""),
            "client_company": payload.get("client_company", ""),
            "lead_id": payload.get("lead_id"),
            "deal_id": payload.get("deal_id"),
            "items": items,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax": tax,
            "total": total,
            "currency": payload.get("currency", "ZAR"),
            "status": "draft",
            "notes": payload.get("notes", ""),
            "issued_at": now.isoformat(),
            "due_date": due_date,
            "paid_at": None,
            "payment_method": None,
        }

        await self._mem.set(f"billing:number:{invoice_number}", invoice_id)

        # Append to index
        ids: list = await self._mem.get("billing:invoices:index") or []
        ids.append(invoice_id)
        await self._mem.set("billing:invoices:index", ids)

        # Generate Paystack payment link if secret key is configured, then persist
        invoice["payment_link"] = await self._paystack_link(invoice)
        await self._mem.set(f"billing:invoice:{invoice_id}", invoice)

        log.info("Invoice created %s total=%.2f %s", invoice_number, total, invoice["currency"])
        return invoice

    async def _paystack_link(self, invoice: dict[str, Any]) -> str | None:
        """Call Paystack /transaction/initialize to get a one-time checkout URL.
        Returns the authorization_url or None if PAYSTACK_SECRET_KEY is not set.
        """
        secret = os.environ.get("PAYSTACK_SECRET_KEY", "")
        if not secret:
            return None
        import httpx
        amount_kobo = int(invoice["total"] * 100)  # Paystack uses smallest currency unit
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "https://api.paystack.co/transaction/initialize",
                    headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                    json={
                        "email": invoice.get("client_email", "client@bridgeai.co.za"),
                        "amount": amount_kobo,
                        "currency": invoice.get("currency", "ZAR"),
                        "reference": invoice["invoice_number"],
                        "metadata": {
                            "invoice_id": invoice["id"],
                            "invoice_number": invoice["invoice_number"],
                            "client_name": invoice.get("client_name", ""),
                        },
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("data", {}).get("authorization_url")
        except Exception:
            log.exception("Paystack link generation failed for %s", invoice.get("invoice_number"))
        return None

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_invoice(self, invoice_id: str) -> dict[str, Any] | None:
        return await self._mem.get(f"billing:invoice:{invoice_id}")

    async def list_invoices(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ids: list = await self._mem.get("billing:invoices:index") or []
        invoices = [await self._mem.get(f"billing:invoice:{i}") for i in ids]
        invoices = [inv for inv in invoices if inv]
        if status:
            invoices = [inv for inv in invoices if inv.get("status") == status]
        # newest first
        invoices.sort(key=lambda x: x.get("issued_at", ""), reverse=True)
        return invoices[offset: offset + limit]

    # ------------------------------------------------------------------
    # Lifecycle mutations
    # ------------------------------------------------------------------

    async def mark_sent(self, invoice_id: str) -> dict[str, Any] | None:
        inv = await self._mem.get(f"billing:invoice:{invoice_id}")
        if not inv:
            return None
        inv["status"] = "sent"
        await self._mem.set(f"billing:invoice:{invoice_id}", inv)
        return inv

    async def mark_paid(
        self,
        invoice_id: str,
        payment_method: str = "manual",
        reference: str = "",
    ) -> dict[str, Any] | None:
        inv = await self._mem.get(f"billing:invoice:{invoice_id}")
        if not inv:
            return None
        inv["status"] = "paid"
        inv["paid_at"] = datetime.utcnow().isoformat()
        inv["payment_method"] = payment_method
        if reference:
            inv["payment_reference"] = reference
        await self._mem.set(f"billing:invoice:{invoice_id}", inv)
        log.info("Invoice %s marked PAID via %s", inv["invoice_number"], payment_method)

        # Auto-collect into treasury
        try:
            from app.services.treasury import TreasuryService
            from app.core.deps import get_memory
            treasury = TreasuryService(get_memory())
            await treasury.collect(
                amount=inv["total"],
                currency=inv["currency"],
                source_project=inv.get("client_company") or "invoice",
                method=payment_method,
                tx_type="invoice_payment",
                meta={"invoice_id": invoice_id, "invoice_number": inv["invoice_number"]},
            )
        except Exception:
            log.exception("Treasury collect failed for invoice %s", invoice_id)

        return inv

    async def reconcile_by_amount(
        self,
        amount: float,
        currency: str,
        payment_method: str,
    ) -> dict[str, Any] | None:
        """Find a sent invoice matching amount+currency and mark it paid (webhook reconciliation)."""
        ids: list = await self._mem.get("billing:invoices:index") or []
        for inv_id in reversed(ids):  # most recent first
            inv = await self._mem.get(f"billing:invoice:{inv_id}")
            if not inv:
                continue
            if (inv.get("status") == "sent"
                    and abs(inv.get("total", 0) - amount) < 0.01
                    and inv.get("currency", "").upper() == currency.upper()):
                return await self.mark_paid(inv_id, payment_method)
        return None

    # ------------------------------------------------------------------
    # Overdue check
    # ------------------------------------------------------------------

    async def flag_overdue(self) -> int:
        """Mark all sent invoices past due date as overdue. Returns count updated."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        ids: list = await self._mem.get("billing:invoices:index") or []
        updated = 0
        for inv_id in ids:
            inv = await self._mem.get(f"billing:invoice:{inv_id}")
            if inv and inv.get("status") == "sent" and inv.get("due_date", "9999") < today:
                inv["status"] = "overdue"
                await self._mem.set(f"billing:invoice:{inv_id}", inv)
                updated += 1
        return updated

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def stats(self) -> dict[str, Any]:
        ids: list = await self._mem.get("billing:invoices:index") or []
        invoices = [await self._mem.get(f"billing:invoice:{i}") for i in ids]
        invoices = [inv for inv in invoices if inv]

        total_billed = sum(inv.get("total", 0) for inv in invoices)
        total_paid = sum(inv.get("total", 0) for inv in invoices if inv.get("status") == "paid")
        by_status: dict[str, int] = {}
        for inv in invoices:
            s = inv.get("status", "draft")
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "total_invoices": len(invoices),
            "total_billed": round(total_billed, 2),
            "total_paid": round(total_paid, 2),
            "outstanding": round(total_billed - total_paid, 2),
            "by_status": by_status,
        }
