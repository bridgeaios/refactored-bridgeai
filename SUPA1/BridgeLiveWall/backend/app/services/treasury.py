"""
Unified treasury collect / status / ledger.
Delegates splits to the process-wide RevenueService (runtime singleton).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from app.services.revenue import DISTRIBUTION_SPLIT


class TreasuryService:
    def __init__(self, memory: Any) -> None:
        self._memory = memory

    async def collect(
        self,
        amount: float,
        currency: str = "BRDG",
        source_project: str = "bridge",
        method: str = "internal",
        type: str = "manual",
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        from app.runtime import revenue_service

        revenue_service.collect(float(amount))
        tx_id = str(uuid.uuid4())
        splits = {k: float(amount) * float(v) for k, v in DISTRIBUTION_SPLIT.items()}
        return {"ok": True, "tx_id": tx_id, "splits": splits}

    async def get_status(self) -> dict[str, Any]:
        from app.runtime import revenue_service

        st = revenue_service.get_status()
        total = float(st.get("balance", 0) or 0) + float(st.get("distributed", 0) or 0)
        buckets = {
            "ubi": float(st.get("ubi", 0) or 0),
            "treasury": float(st.get("treasury", 0) or 0),
            "ops": float(st.get("ops", 0) or 0),
            "founder": float(st.get("founder", 0) or 0),
        }
        return {"ok": True, "total": total, "buckets": buckets, **st}

    async def get_ledger(self, limit: int = 50) -> list[dict]:
        return []

    async def disburse(
        self,
        bucket: str,
        amount: float,
        destination: str,
        authorized_by: str,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "bucket": bucket,
            "amount": amount,
            "destination": destination,
            "authorized_by": authorized_by,
        }
