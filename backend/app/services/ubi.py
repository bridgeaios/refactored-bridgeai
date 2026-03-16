"""
UBI Service – distributes BRDG tokens periodically
Aligns with UN SDG 1: No Poverty
This is a lightweight, simulated service used by the API.
In production this would integrate with the blockchain service to mint
and transfer tokens, persist claim timestamps to a DB, and enforce rate limits.
"""
import time


class UbiService:
    def __init__(self):
        self.period = 86400  # seconds (daily)
        self.amount = 100  # BRDG tokens per claim (simulated)
        self._last_claim: dict[str, float] = {}  # address -> timestamp

    def can_claim(self, address: str) -> bool:
        last = self._last_claim.get(address)
        if last is None:
            return True
        return (time.time() - last) >= self.period

    def distribute(self, address: str) -> int:
        """Simulate distribution and return amount distributed.

        Real implementation would create a blockchain transaction and return
        tx metadata.
        """
        if not address:
            raise ValueError("address required")
        if not self.can_claim(address):
            return 0
        self._last_claim[address] = time.time()
        # In a real system: call BlockchainService.mint_and_send(...)
        return self.amount
