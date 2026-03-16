"""
Revenue Engines – collect fees from marketplace/DeFi yields.
Funds UBI, treasury, ops, and founder. Auto-distributes on collect.

UNIFIED: All calls to collect() also route to TreasuryService via an optional
on_collect callback. Set this at startup in runtime.py.
"""
from __future__ import annotations
from typing import Any, Callable, Coroutine

# Split ratios: UBI, Treasury, Ops, Founder (must sum to 1.0)
DISTRIBUTION_SPLIT = {
    "ubi": 0.40,
    "treasury": 0.30,
    "ops": 0.20,
    "founder": 0.10,
}


class RevenueService:
    def __init__(self) -> None:
        self.balance = 0.0
        self.distributed = 0.0
        self.ubi = 0.0
        self.treasury = 0.0
        self.ops = 0.0
        self.founder = 0.0
        # Optional async callback: called with (amount, source, method) after collect
        self._on_collect: Callable[..., Coroutine[Any, Any, Any]] | None = None

    def set_treasury_callback(self, cb: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """Wire treasury_service.collect into revenue flow at startup."""
        self._on_collect = cb

    def collect(self, amount: float, source: str = "bridge-api", method: str = "internal") -> float:
        """Collect revenue and distribute to buckets. Returns amount collected."""
        if amount <= 0:
            return 0.0
        self.balance += amount
        self._auto_distribute(amount)
        if self._on_collect:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._on_collect(amount, source, method))
            except Exception:
                pass
        return amount

    def _auto_distribute(self, amount: float) -> None:
        for bucket, ratio in DISTRIBUTION_SPLIT.items():
            portion = amount * ratio
            if bucket == "ubi":
                self.ubi += portion
            elif bucket == "treasury":
                self.treasury += portion
            elif bucket == "ops":
                self.ops += portion
            elif bucket == "founder":
                self.founder += portion
        self.distributed += amount

    def get_status(self) -> dict[str, float]:
        return {
            "balance": self.balance,
            "distributed": self.distributed,
            "ubi": self.ubi,
            "treasury": self.treasury,
            "ops": self.ops,
            "founder": self.founder,
        }

    def distribute_to_ubi(self, amount: float) -> bool:
        """Legacy: manually add to UBI pool."""
        if amount <= 0:
            return False
        self.ubi += amount
        self.distributed += amount
        return True
