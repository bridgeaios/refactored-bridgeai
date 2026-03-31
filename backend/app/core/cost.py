"""
cost.py — Gap 14: Cost Accounting Layer.

Tracks compute cost per agent action, per worker cycle, and per channel.
Costs are stored in MemoryStore under structured keys and aggregated on demand.

Cost taxonomy (aligned with emit channels):
  J (Job)      — worker task execution, scraping, data pipeline
  X (Agent)    — AI inference cycles, OSINT analysis, LLM calls
  P (Pipeline) — CRM stage transitions, lead scoring
  F (Finance)  — treasury operations, payment processing, trading

Each cost entry carries:
  channel, label, amount, cycle, window, ts, ref_id (optional)

Usage:
    from app.core.cost import record_cost, cost_summary, cost_budget_ok

    await record_cost(mem, channel="J", label="scrape_site", amount=0.001)
    ok = await cost_budget_ok(mem, channel="X", proposed=0.05)  # daily cap check
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.core.clock import current_cycle, current_window

_PREFIX      = "cost:entry:"
_INDEX       = "cost:index"
_DAILY_INDEX = "cost:daily:"   # cost:daily:<cycle>:<channel>

# Daily budget caps per channel (in abstract cost units)
# These act as circuit-breakers: if the day's spend exceeds the cap,
# emit_agent / emit_job will be suppressed automatically.
DAILY_CAPS: dict[str, float] = {
    "J": 100.0,   # up to 100 units of job cost per cycle
    "X": 50.0,    # agent inference is expensive — tighter cap
    "P": 200.0,   # pipeline transitions are cheap
    "F": 500.0,   # finance ops capped high — treasury manages its own gates
}


async def record_cost(
    mem,
    channel: str,
    label: str,
    amount: float,
    ref_id: str | None = None,
) -> dict:
    """Record a cost entry against a channel for the current cycle."""
    entry_id = f"{int(time.time()*1000)}-{channel}-{label[:20]}"
    entry = {
        "id":      entry_id,
        "channel": channel,
        "label":   label,
        "amount":  round(amount, 8),
        "cycle":   current_cycle(),
        "window":  current_window().value,
        "ts":      time.time(),
        "ref_id":  ref_id,
    }

    await mem.set(_PREFIX + entry_id, json.dumps(entry))

    # Append to main index
    raw_index = await mem.get(_INDEX)
    index: list[str] = json.loads(raw_index) if raw_index else []
    index.append(entry_id)
    # Keep last 10 000 entries
    if len(index) > 10_000:
        index = index[-10_000:]
    await mem.set(_INDEX, json.dumps(index))

    # Accumulate daily total
    daily_key = _DAILY_INDEX + f"{current_cycle()}:{channel}"
    raw_daily = await mem.get(daily_key)
    daily_total = float(raw_daily) if raw_daily else 0.0
    await mem.set(daily_key, str(round(daily_total + amount, 8)))

    return entry


async def cost_summary(mem, cycle: int | None = None) -> dict[str, Any]:
    """Return per-channel cost totals for the given cycle (default: today)."""
    c = cycle if cycle is not None else current_cycle()
    result: dict[str, float] = {}
    for ch in ("J", "X", "P", "F"):
        raw = await mem.get(_DAILY_INDEX + f"{c}:{ch}")
        result[ch] = round(float(raw), 6) if raw else 0.0
    return {
        "cycle":   c,
        "totals":  result,
        "caps":    DAILY_CAPS,
        "headroom": {ch: round(DAILY_CAPS[ch] - result.get(ch, 0), 6) for ch in DAILY_CAPS},
    }


async def cost_budget_ok(mem, channel: str, proposed: float) -> bool:
    """
    Return True if adding `proposed` cost to `channel` stays within the daily cap.
    Used as a second gate alongside emit() — even a value-positive action may
    be suppressed if the channel is over budget.
    """
    cap = DAILY_CAPS.get(channel)
    if cap is None:
        return True  # unknown channel — don't block
    daily_key = _DAILY_INDEX + f"{current_cycle()}:{channel}"
    raw = await mem.get(daily_key)
    current_spend = float(raw) if raw else 0.0
    return (current_spend + proposed) <= cap


async def cost_recent(mem, limit: int = 50) -> list[dict]:
    """Return the most recent cost entries."""
    raw_index = await mem.get(_INDEX)
    index: list[str] = json.loads(raw_index) if raw_index else []
    entries = []
    for entry_id in reversed(index[-limit:]):
        raw = await mem.get(_PREFIX + entry_id)
        if raw:
            try:
                entries.append(json.loads(raw))
            except Exception:
                import logging as _log
                _log.getLogger(__name__).warning("[COST] corrupt entry %s — skipped", entry_id)
    return entries
