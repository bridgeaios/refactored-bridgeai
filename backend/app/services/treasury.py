"""
Unified Treasury — single source of truth for all revenue across all projects.

Every project (BridgeLiveWall, AOE, Supaco, Taurus, Next.js, etc.) routes all
revenue through TreasuryService.collect(). One ledger, one split, one spine.

Split: UBI 40% · Treasury 30% · Ops 20% · Founder 10%
Rails: internal (BRDG), paystack, paypal, crypto, subscription, sensor, trade
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any

from app.core.emit import emit_finance

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

LEDGER_KEY = "treasury:ledger"
STATUS_KEY = "treasury:status"
MAX_LEDGER = 1000

SPLIT: dict[str, float] = {
    "ubi": 0.40,
    "treasury": 0.30,
    "ops": 0.20,
    "founder": 0.10,
}

# Supported payment methods / rails
RAILS = {"internal", "paystack", "paypal", "crypto", "subscription", "sensor", "trade", "marketplace", "manual"}

# Currency conversion to BRDG (approximate; update with real oracle in prod)
CURRENCY_TO_BRDG: dict[str, float] = {
    "BRDG": 1.0,
    "USD": 10.0,    # 1 USD = 10 BRDG
    "ZAR": 0.55,    # 1 ZAR = 0.55 BRDG
    "EUR": 11.0,    # 1 EUR = 11 BRDG
    "GBP": 12.5,    # 1 GBP = 12.5 BRDG
    "ETH": 50000.0, # 1 ETH = 50000 BRDG
    "BTC": 800000.0,
    "SOL": 2000.0,
}


class TreasuryService:
    """
    Unified treasury for all Bridge AI OS projects.
    All revenue flows through collect(). All projects share one ledger.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def collect(
        self,
        amount: float,
        currency: str = "BRDG",
        source_project: str = "bridge-api",
        method: str = "internal",
        type_: str = "revenue",
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Collect revenue from any project into the unified treasury.
        Converts to BRDG, applies split, appends to ledger.
        Returns the ledger entry.
        """
        if amount <= 0:
            return {"ok": False, "reason": "amount must be > 0"}

        # Emit gate (Finance channel): enforce value-positive execution
        if not emit_finance(values=[amount], cost=0.0):
            return {"ok": False, "reason": "emit_gate: non-positive value"}

        currency = currency.upper()
        rate = CURRENCY_TO_BRDG.get(currency, 1.0)
        brdg_amount = round(amount * rate, 6)

        split = {k: round(brdg_amount * v, 6) for k, v in SPLIT.items()}

        entry: dict[str, Any] = {
            "id": _tx_id(source_project, amount, currency),
            "ts": _now(),
            "ts_epoch": time.time(),
            "source_project": source_project,
            "method": method if method in RAILS else "internal",
            "type": type_,
            "amount_original": amount,
            "currency": currency,
            "amount_brdg": brdg_amount,
            "split": split,
            "meta": meta or {},
        }

        await self._append_ledger(entry)
        await self._update_status(entry)
        return {"ok": True, "entry": entry}

    async def get_status(self) -> dict[str, Any]:
        """Return aggregated treasury status: totals, by-project, by-method, by-currency, buckets."""
        raw = await self._memory.get(STATUS_KEY)
        if isinstance(raw, str) and raw:
            try:
                return json.loads(raw)  # type: ignore[no-any-return]
            except Exception:
                pass
        return _empty_status()

    async def get_ledger(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return most recent ledger entries (most recent first)."""
        entries = await self._memory.get_recent(LEDGER_KEY, min(limit, MAX_LEDGER))
        return list(reversed(entries))

    async def disburse(
        self,
        bucket: str,
        amount: float,
        destination: str,
        authorized_by: str = "founder",
    ) -> dict[str, Any]:
        """
        Record a treasury disbursement (payout from a bucket).
        In production: triggers real transfer via payment rail.
        """
        if bucket not in SPLIT:
            return {"ok": False, "reason": f"unknown bucket: {bucket}"}
        if amount <= 0:
            return {"ok": False, "reason": "amount must be > 0"}

        record: dict[str, Any] = {
            "id": _tx_id("disburse", amount, bucket),
            "ts": _now(),
            "ts_epoch": time.time(),
            "type": "disbursement",
            "bucket": bucket,
            "amount_brdg": amount,
            "destination": destination,
            "authorized_by": authorized_by,
        }
        await self._append_ledger(record)
        # Deduct from status bucket
        status = await self.get_status()
        buckets = status.get("buckets", {})
        current = float(buckets.get(bucket, 0))
        buckets[bucket] = max(0.0, round(current - amount, 6))
        status["buckets"] = buckets
        await self._memory.set(STATUS_KEY, json.dumps(status))
        return {"ok": True, "record": record}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _append_ledger(self, entry: dict[str, Any]) -> None:
        await self._memory.append(LEDGER_KEY, entry)

    async def _update_status(self, entry: dict[str, Any]) -> None:
        status = await self.get_status()
        brdg = entry["amount_brdg"]
        split = entry["split"]
        proj = entry["source_project"]
        method = entry["method"]
        currency = entry["currency"]

        status["total_collected_brdg"] = round(status.get("total_collected_brdg", 0.0) + brdg, 6)
        status["total_tx"] = status.get("total_tx", 0) + 1

        # Buckets
        buckets = status.setdefault("buckets", dict.fromkeys(SPLIT, 0.0))
        for k, v in split.items():
            buckets[k] = round(float(buckets.get(k, 0.0)) + v, 6)

        # By project
        by_project: dict[str, float] = status.setdefault("by_project", {})
        by_project[proj] = round(float(by_project.get(proj, 0.0)) + brdg, 6)

        # By method/rail
        by_method: dict[str, float] = status.setdefault("by_method", {})
        by_method[method] = round(float(by_method.get(method, 0.0)) + brdg, 6)

        # By currency
        by_currency: dict[str, float] = status.setdefault("by_currency", {})
        by_currency[currency] = round(float(by_currency.get(currency, 0.0)) + entry["amount_original"], 6)

        status["last_tx_ts"] = entry["ts"]
        await self._memory.set(STATUS_KEY, json.dumps(status))


def _empty_status() -> dict[str, Any]:
    return {
        "total_collected_brdg": 0.0,
        "total_tx": 0,
        "buckets": dict.fromkeys(SPLIT, 0.0),
        "by_project": {},
        "by_method": {},
        "by_currency": {},
        "last_tx_ts": None,
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _tx_id(prefix: str, amount: float, suffix: str) -> str:
    raw = f"{prefix}:{amount}:{suffix}:{time.time()}"
    return "tx_" + hashlib.sha256(raw.encode()).hexdigest()[:16]
