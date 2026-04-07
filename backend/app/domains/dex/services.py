"""
DEX Service -- auto-dex BRDG -> ETH, SOL, USDC, etc.
All twins share this: swap Bridge token to native or stable assets.
Simulated for now; production would integrate 1inch, Uniswap, Jupiter, etc.

Ported from BRIDGE_AI_OS/core/app/services/dex.py.
"""
from __future__ import annotations

from typing import Dict

# Simulated rates: 1 BRDG ~ X target (placeholder; real = oracle/DEX)
RATES: Dict[str, float] = {
    "ETH": 0.0003,   # 1 BRDG ~ 0.0003 ETH
    "SOL": 0.002,    # 1 BRDG ~ 0.002 SOL
    "USDC": 0.15,    # 1 BRDG ~ $0.15
    "USDT": 0.15,
    "MATIC": 0.2,
    "AVAX": 0.001,
    "BNB": 0.0002,
}


class DexService:
    def __init__(self) -> None:
        # Simulated BRDG balance per wallet (in production: read from chain)
        self._balances: Dict[str, float] = {}
        self._swap_history: list = []

    def get_balance(self, address: str) -> float:
        """Get BRDG balance for address. Simulated; production reads chain."""
        if not address:
            return 0.0
        return self._balances.get(address, 0.0)

    def credit_brdg(self, address: str, amount: float) -> float:
        """Credit BRDG to wallet (e.g. from UBI claim)."""
        if not address or amount <= 0:
            return 0.0
        self._balances[address] = self._balances.get(address, 0.0) + amount
        return self._balances[address]

    def swap(
        self,
        address: str,
        from_token: str,
        to_token: str,
        amount: float,
    ) -> Dict:
        """
        Swap tokens. BRDG -> ETH, SOL, USDC, etc.
        Returns {ok, received, tx_id?, error?}
        """
        if not address:
            return {"ok": False, "error": "address required"}
        if from_token.upper() != "BRDG":
            return {"ok": False, "error": "Only BRDG -> other supported"}
        to_upper = to_token.upper()
        if to_upper not in RATES:
            return {"ok": False, "error": f"Unsupported target: {to_token}. Use ETH, SOL, USDC, USDT, MATIC, AVAX, BNB"}

        amount = float(amount)
        if amount <= 0:
            return {"ok": False, "error": "amount must be positive"}

        bal = self.get_balance(address)
        if bal < amount:
            return {"ok": False, "error": f"Insufficient BRDG. Balance: {bal:.2f}"}

        rate = RATES[to_upper]
        received = amount * rate
        # Simulate 0.3% slippage
        received *= 0.997

        self._balances[address] = bal - amount
        tx_id = f"0x{hash((address, amount, to_upper)) % (16**64):064x}"
        self._swap_history.append({
            "address": address,
            "from": from_token,
            "to": to_upper,
            "amount": amount,
            "received": received,
            "tx_id": tx_id,
        })

        return {
            "ok": True,
            "received": round(received, 8),
            "to_token": to_upper,
            "tx_id": tx_id,
        }

    def get_rates(self) -> Dict[str, float]:
        """Return current swap rates (1 BRDG = X target)."""
        return dict(RATES)


dex_service = DexService()
