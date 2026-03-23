"""
UBI Service – distributes BRDG tokens periodically
Aligns with UN SDG 1: No Poverty
This is a lightweight, simulated service used by the API.
In production this would integrate with the blockchain service to mint
and transfer tokens, persist claim timestamps to a DB, and enforce rate limits.
"""
import time
from typing import Optional, Any


class UbiService:
    def __init__(self):
        self.period = 86400  # seconds (daily)
        # Default claim amount (BRDG). Actual payout is capped by treasury UBI bucket.
        self.amount = 100
        self._last_claim: dict[str, float] = {}  # address -> timestamp
        self._treasury = None

    def can_claim(self, address: str) -> bool:
        last = self._last_claim.get(address)
        if last is None:
            return True
        return (time.time() - last) >= self.period

    def set_treasury(self, treasury: Any) -> None:
        """
        Wire unified treasury into UBI.
        Expected interface:
          - await treasury.get_status()
          - await treasury.disburse(bucket="ubi", amount=<float>, destination=<str>, authorized_by=<str>)
        """
        self._treasury = treasury

    async def distribute(self, address: str) -> int:
        """
        Distribute UBI and return amount distributed.

        Deterministic economics:
        - UBI is paid *from* the unified Treasury UBI bucket (40% inflow split).
        - No treasury funds => no payout (no money printing in the control loop).
        """
        if not address:
            raise ValueError("address required")
        if not self.can_claim(address):
            return 0

        payout = int(self.amount)
        # If treasury is wired, cap by available UBI bucket and record disbursement.
        if self._treasury is not None:
            try:
                status = await self._treasury.get_status()
                buckets = status.get("buckets", {}) if isinstance(status, dict) else {}
                available = float(buckets.get("ubi", 0.0) or 0.0)
            except Exception:
                available = 0.0
            if available <= 0:
                return 0
            payout = int(min(float(payout), available))
            if payout <= 0:
                return 0
            try:
                await self._treasury.disburse(
                    bucket="ubi",
                    amount=float(payout),
                    destination=str(address),
                    authorized_by="ubi_service",
                )
            except Exception:
                # If we can't debit treasury, don't pay out.
                return 0

        self._last_claim[address] = time.time()
        return int(payout)
