"""
Economy domain service facade.
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from app.core.errors import NotFoundError, ValidationError
from app.services.treasury import TreasuryService

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore


class EconomyServices:
    """Aggregates economy-domain services."""

    def __init__(self, memory: "MemoryStore") -> None:
        from app.runtime import marketplace_service, twins_competition, ubi_service

        self._memory = memory
        self._treasury = TreasuryService(memory)
        self._ubi = ubi_service
        self._marketplace = marketplace_service
        self._competition = twins_competition

    async def collect(
        self,
        amount: float,
        currency: str = "BRDG",
        source_project: str = "bridge",
        method: str = "internal",
        type: str = "manual",
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        if amount <= 0:
            raise ValidationError(f"amount must be positive, got {amount}")
        return await self._treasury.collect(
            amount=amount,
            currency=currency,
            source_project=source_project,
            method=method,
            type=type,
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

    async def ubi_can_claim(self, address: str) -> bool:
        return self._ubi.can_claim(address)

    async def ubi_distribute(self, address: str) -> dict[str, Any]:
        if not address:
            raise ValidationError("address is required")
        amount = self._ubi.distribute(address)
        return {"ok": True, "amount": float(amount)}

    async def ubi_status(self, address: str) -> dict[str, Any]:
        return {
            "can_claim": self._ubi.can_claim(address),
            "amount": self._ubi.amount,
            "period_seconds": self._ubi.period,
        }

    def get_tasks(self, twin_id: str = "system", status: Optional[str] = None) -> list[dict]:
        _ = twin_id
        return self._marketplace.get_tasks(status=status or "open")

    def post_task(
        self,
        title: str,
        value: float,
        twin_id: str = "system",
        tags: Optional[list] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        task = {
            "title": title,
            "reward": value,
            "posted_by": twin_id,
            "tags": tags or [],
            **(meta or {}),
        }
        t = self._marketplace.add_task(task)
        return {"ok": True, "task_id": t["id"], "task": t}

    def accept_task(self, task_id: int, twin_id: str) -> dict[str, Any]:
        task = self._marketplace.accept_task(task_id=task_id, wallet=twin_id)
        if task is None:
            raise NotFoundError(f"task {task_id} not found or not available")
        return {"ok": True, "task": task}

    def complete_task(
        self,
        task_id: int,
        twin_id: str = "system",
        result: Optional[str] = None,
    ) -> dict[str, Any]:
        _ = twin_id
        _ = result
        task = self._competition.complete_task(int(task_id), self._marketplace)
        if task is None:
            raise NotFoundError(f"task {task_id} not found or not in_progress")
        return {"ok": True, "task": task}

    def get_task(self, task_id: int) -> dict[str, Any]:
        tasks = self._marketplace.get_tasks(status="all")
        for t in tasks:
            if t.get("id") == task_id:
                return t
        raise NotFoundError(f"task {task_id} not found")

    async def revenue_summary(self) -> dict[str, Any]:
        from app.runtime import revenue_service

        return revenue_service.get_status()
