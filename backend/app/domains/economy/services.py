"""
Economy domain service facade.

Wraps TreasuryService, UbiService, MarketplaceService, RevenueService
behind a single interface consumed by domain routes via Depends().

Raises BridgeError subclasses — never bare Exception.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.errors import NotFoundError, ValidationError
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
