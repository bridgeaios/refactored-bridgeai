"""
clock.py — Gap 13: Time System / Cycles / Settlement Windows.

Defines the BridgeAI temporal model:

  Epoch      — fixed genesis timestamp (2025-01-01T00:00:00Z)
  Cycle      — 24-hour operational period (day-indexed from epoch)
  Window     — named sub-cycle slot: MORNING | AFTERNOON | EVENING | NIGHT
  Settlement — end-of-cycle settlement, triggered at 23:45 SAST

The clock is purely deterministic from wall-clock time — no external state
required. Workers and treasury use these primitives to stamp ledger entries
and enforce settlement boundaries.

Usage:
    from app.core.clock import current_cycle, current_window, is_settlement_time, CycleWindow

    cycle = current_cycle()          # e.g. 453
    window = current_window()        # CycleWindow.AFTERNOON
    settling = is_settlement_time()  # True in last 15 min of cycle
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from enum import Enum

# ── Constants ────────────────────────────────────────────────────────────────

# Genesis timestamp: 2025-01-01 00:00:00 UTC
_EPOCH_UTC: float = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()

# SAST = UTC+2
_SAST = timezone(timedelta(hours=2))

# Settlement window: last 15 minutes of each SAST day (23:45–00:00)
_SETTLEMENT_HOUR   = 23
_SETTLEMENT_MINUTE = 45


# ── Cycle window taxonomy ────────────────────────────────────────────────────

class CycleWindow(str, Enum):
    MORNING   = "MORNING"    # 06:00–12:00 SAST
    AFTERNOON = "AFTERNOON"  # 12:00–18:00 SAST
    EVENING   = "EVENING"    # 18:00–24:00 SAST
    NIGHT     = "NIGHT"      # 00:00–06:00 SAST


_WINDOW_SCHEDULE: list[tuple[int, int, CycleWindow]] = [
    (0,  6,  CycleWindow.NIGHT),
    (6,  12, CycleWindow.MORNING),
    (12, 18, CycleWindow.AFTERNOON),
    (18, 24, CycleWindow.EVENING),
]


# ── Public API ────────────────────────────────────────────────────────────────

def current_cycle() -> int:
    """Return the current cycle number (day index since epoch)."""
    elapsed = time.time() - _EPOCH_UTC
    return max(0, int(elapsed // 86400))


def cycle_start_ts(cycle: int) -> float:
    """Return the UTC timestamp of when a cycle started."""
    return _EPOCH_UTC + cycle * 86400


def cycle_end_ts(cycle: int) -> float:
    """Return the UTC timestamp of when a cycle ends."""
    return _EPOCH_UTC + (cycle + 1) * 86400


def current_window() -> CycleWindow:
    """Return the active CycleWindow for the current SAST hour."""
    now_sast = datetime.now(_SAST)
    h = now_sast.hour
    for start, end, window in _WINDOW_SCHEDULE:
        if start <= h < end:
            return window
    return CycleWindow.EVENING


def is_settlement_time() -> bool:
    """Return True if we are in the settlement window (SAST 23:45–00:00)."""
    now_sast = datetime.now(_SAST)
    return now_sast.hour == _SETTLEMENT_HOUR and now_sast.minute >= _SETTLEMENT_MINUTE


def now_sast_iso() -> str:
    """Return the current SAST time as an ISO-8601 string."""
    return datetime.now(_SAST).isoformat()


def cycle_info() -> dict:
    """Return a full snapshot of the current cycle state."""
    cycle = current_cycle()
    return {
        "cycle":        cycle,
        "window":       current_window().value,
        "settling":     is_settlement_time(),
        "cycle_start":  cycle_start_ts(cycle),
        "cycle_end":    cycle_end_ts(cycle),
        "now_sast":     now_sast_iso(),
        "now_utc":      datetime.now(timezone.utc).isoformat(),
        "elapsed_s":    round(time.time() - cycle_start_ts(cycle), 1),
        "remaining_s":  round(cycle_end_ts(cycle) - time.time(), 1),
    }


def stamp() -> dict:
    """Minimal timestamp dict for ledger entries."""
    return {
        "ts":    time.time(),
        "cycle": current_cycle(),
        "win":   current_window().value,
    }
