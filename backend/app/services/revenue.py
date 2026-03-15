"""
Revenue Engines – collect fees from marketplace/DeFi yields
Funds UBI, treasury, ops, and founder. Auto-distributes on collect.
"""
from typing import Dict

# Split ratios: UBI, Treasury, Ops, Founder (must sum to 1.0)
DISTRIBUTION_SPLIT = {
    "ubi": 0.40,
    "treasury": 0.30,
    "ops": 0.20,
    "founder": 0.10,
}


class RevenueService:
    def __init__(self):
        self.balance = 0.0  # simulated BRDG balance (pre-split)
        self.distributed = 0.0  # total distributed (legacy)
        self.ubi = 0.0
        self.treasury = 0.0
        self.ops = 0.0
        self.founder = 0.0

    def collect(self, amount: float) -> float:
        """Simulate collection of fees/yields; returns amount collected. Auto-distributes to UBI, treasury, ops, founder."""
        if amount <= 0:
            return 0.0
        self.balance += amount
        self._auto_distribute(amount)
        return amount

    def _auto_distribute(self, amount: float) -> None:
        """Split amount across UBI, treasury, ops, founder."""
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

    def get_status(self) -> Dict[str, float]:
        return {
            "balance": self.balance,
            "distributed": self.distributed,
            "ubi": self.ubi,
            "treasury": self.treasury,
            "ops": self.ops,
            "founder": self.founder,
        }

    def distribute_to_ubi(self, amount: float) -> bool:
        """Legacy: manually add to UBI (e.g. from trade flow). Prefer collect() which auto-distributes."""
        if amount <= 0:
            return False
        self.ubi += amount
        self.distributed += amount
        return True
