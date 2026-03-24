"""
Economy domain service facade.

Wraps TreasuryService, UbiService, MarketplaceService, RevenueService
behind a single interface consumed by domain routes via Depends().

Raises BridgeError subclasses — never bare Exception.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.errors import AuthError, NotFoundError, ValidationError
from app.services.marketplace import MarketplaceService
from app.services.revenue import RevenueService
from app.services.treasury import TreasuryService
from app.services.ubi import UbiService

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


class EconomyServices:
    """Aggregates all economy-domain services. Singleton via get_economy() in deps.py."""

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory
        self._treasury = TreasuryService(memory)
        self._ubi = UbiService()
        self._ubi.set_treasury(self._treasury)
        self._marketplace = MarketplaceService()
        self._revenue = RevenueService()

    # ------------------------------------------------------------------
    # Treasury
    # ------------------------------------------------------------------

    async def collect(
        self,
        amount: float,
        currency: str = "BRDG",
        source_project: str = "bridge",
        method: str = "internal",
        type: str = "manual",
        meta: dict | None = None,
    ) -> dict[str, Any]:
        if amount <= 0:
            raise ValidationError(f"amount must be positive, got {amount}")
        return await self._treasury.collect(
            amount=amount,
            currency=currency,
            source_project=source_project,
            method=method,
            type_=type,
            meta=meta or {},
        )

    async def treasury_status(self) -> dict[str, Any]:
        return await self._treasury.get_status()

    async def treasury_ledger(self, limit: int = 50) -> list[dict]:
        return await self._treasury.get_ledger(limit=limit)

    async def treasury_disburse(
        self,
        bucket: str,
        amount: float,
        destination: str,
        authorized_by: str,
    ) -> dict[str, Any]:
        return await self._treasury.disburse(
            bucket=bucket,
            amount=amount,
            destination=destination,
            authorized_by=authorized_by,
        )

    # ------------------------------------------------------------------
    # UBI
    # ------------------------------------------------------------------

    async def ubi_can_claim(self, address: str) -> bool:
        return self._ubi.can_claim(address)

    async def ubi_distribute(self, address: str) -> dict[str, Any]:
        if not address:
            raise ValidationError("address is required")
        amount = await self._ubi.distribute(address)
        return {"ok": True, "amount": amount}

    async def ubi_status(self, address: str) -> dict[str, Any]:
        return {
            "can_claim": self._ubi.can_claim(address),
            "amount": self._ubi.amount,
            "period_seconds": self._ubi.period,
        }

    # ------------------------------------------------------------------
    # Marketplace
    # ------------------------------------------------------------------

    def get_tasks(self, twin_id: str = "system", status: str | None = None) -> list[dict]:
        return self._marketplace.get_tasks(twin_id=twin_id, status=status)

    def post_task(
        self,
        title: str,
        value: float,
        twin_id: str = "system",
        tags: list | None = None,
        meta: dict | None = None,
    ) -> dict[str, Any]:
        task = self._marketplace.add_task({
            "title": title,
            "value": value,
            "posted_by": twin_id,
            "tags": tags or [],
            **(meta or {}),
        })
        return {"ok": True, "task_id": task["id"], "task": task}

    def accept_task(self, task_id: int, twin_id: str) -> dict[str, Any]:
        task = self._marketplace.accept_task(task_id=task_id, wallet=twin_id)
        if task is None:
            raise NotFoundError(f"task {task_id} not found or not available")
        return {"ok": True, "task": task}

    def complete_task(
        self, task_id: int, twin_id: str = "system", result: str | None = None
    ) -> dict[str, Any]:
        task = self._marketplace.complete_task(task_id=task_id)
        if task is None:
            raise NotFoundError(f"task {task_id} not found or not in_progress")
        return {"ok": True, "task": task}

    def get_task(self, task_id: int) -> dict[str, Any]:
        tasks = self._marketplace.get_tasks(status="all")
        for t in tasks:
            if t.get("id") == task_id:
                return t
        raise NotFoundError(f"task {task_id} not found")

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------

    async def revenue_summary(self) -> dict[str, Any]:
        return self._revenue.get_status()

    # ------------------------------------------------------------------
    # Treasury controls + rails
    # ------------------------------------------------------------------

    def list_rails(self) -> dict[str, Any]:
        import os
        rails = [
            {"id": "internal", "label": "Internal (BRDG)", "status": "active", "currencies": ["BRDG"]},
            {"id": "paystack", "label": "Paystack", "status": "active" if os.environ.get("PAYSTACK_SECRET_KEY") else "no-key", "currencies": ["ZAR", "NGN", "USD", "GHS"]},
            {"id": "paypal", "label": "PayPal", "status": "active" if os.environ.get("PAYPAL_CLIENT_ID") else "no-key", "currencies": ["USD", "EUR", "GBP"]},
            {"id": "crypto", "label": "Crypto (BRDG/ETH/SOL)", "status": "active", "currencies": ["BRDG", "ETH", "BTC", "SOL"]},
            {"id": "subscription", "label": "Subscription revenue", "status": "active", "currencies": ["USD", "ZAR", "BRDG"]},
            {"id": "sensor", "label": "Sensor / passive income", "status": "active", "currencies": ["BRDG"]},
            {"id": "trade", "label": "Boss-bot trade fees", "status": "active", "currencies": ["BRDG"]},
            {"id": "marketplace", "label": "Marketplace fees", "status": "active", "currencies": ["BRDG"]},
        ]
        return {"ok": True, "rails": rails, "split": {"ubi": "40%", "treasury": "30%", "ops": "20%", "founder": "10%"}}

    # ------------------------------------------------------------------
    # Payment webhooks
    # ------------------------------------------------------------------

    async def webhook_paystack(self, body: bytes, signature: str) -> dict[str, Any]:
        import json as _json
        from app.services.payment_rails import PaymentRails
        if not PaymentRails.verify_paystack(body, signature):
            raise AuthError("invalid Paystack signature")
        try:
            payload = _json.loads(body)
        except Exception as exc:
            raise ValidationError("invalid JSON") from exc
        event = PaymentRails.parse_paystack(payload)
        if not event:
            return {"ok": True, "skipped": True, "reason": "non-payment event"}
        result = await self._treasury.collect(
            amount=event["amount"],
            currency=event["currency"],
            source_project=event.get("plan") or "paystack-direct",
            method="paystack",
            type_=event["type"],
            meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
        )
        return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}

    async def webhook_paypal(self, body: bytes, headers: dict) -> dict[str, Any]:
        import json as _json
        from app.services.payment_rails import PaymentRails
        if not PaymentRails.verify_paypal(body, headers):
            raise AuthError("invalid PayPal signature")
        try:
            payload = _json.loads(body)
        except Exception as exc:
            raise ValidationError("invalid JSON") from exc
        event = PaymentRails.parse_paypal(payload)
        if not event or event["amount"] <= 0:
            return {"ok": True, "skipped": True, "reason": "non-payment or zero-amount event"}
        result = await self._treasury.collect(
            amount=event["amount"],
            currency=event["currency"],
            source_project=event.get("plan") or "paypal-direct",
            method="paypal",
            type_=event["type"],
            meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
        )
        return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}

    async def webhook_crypto(self, body: bytes) -> dict[str, Any]:
        import json as _json
        from app.services.payment_rails import PaymentRails
        try:
            payload = _json.loads(body)
        except Exception as exc:
            raise ValidationError("invalid JSON") from exc
        event = PaymentRails.parse_crypto(payload)
        if not event:
            return {"ok": True, "skipped": True, "reason": "unrecognized crypto event"}
        result = await self._treasury.collect(
            amount=event["amount"],
            currency=event["currency"],
            source_project="crypto",
            method="crypto",
            type_=event["type"],
            meta={"wallet": event["customer"], "tx_hash": event["reference"], **event.get("meta", {})},
        )
        return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}

    async def webhook_generic(self, rail: str, body: bytes, source_project: str | None = None) -> dict[str, Any]:
        import json as _json
        from app.services.payment_rails import PaymentRails
        try:
            payload = _json.loads(body)
        except Exception as exc:
            raise ValidationError("invalid JSON") from exc
        event = PaymentRails.normalize(payload, rail)
        if not event:
            raise ValidationError("amount required")
        result = await self._treasury.collect(
            amount=event["amount"],
            currency=event["currency"],
            source_project=source_project or rail,
            method=rail,
            type_=event["type"],
            meta={"customer": event["customer"], "reference": event["reference"], **event.get("meta", {})},
        )
        return {"ok": True, "collected": result.get("entry", {}).get("amount_brdg", 0)}
