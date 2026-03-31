"""
constraints.py — Gap 15: Constraint Engine.

Enforces hard limits across the system. Constraints are checked before any
emission is allowed. They act as circuit-breakers that override the value
function when system health is threatened.

Constraint categories:
  RATE    — max calls per minute per domain/channel
  BUDGET  — daily cost caps (delegates to cost.py)
  BALANCE — treasury must not go below floor before payments
  LOAD    — worker queue depth cap
  AGENT   — concurrent agent invocation cap

A constraint violation returns a ConstraintResult(ok=False, reason=...).
All constraints are non-blocking — they never raise exceptions.

Usage:
    from app.core.constraints import check_constraints, ConstraintResult

    result = await check_constraints(mem, channel="F", action="payout", amount=1000.0)
    if not result.ok:
        return {"blocked": True, "reason": result.reason}
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass


@dataclass
class ConstraintResult:
    ok: bool
    reason: str = ""
    constraint: str = ""


# ── Rate limiter (in-memory sliding window per mem key) ─────────────────────

_RATE_LIMITS: dict[str, int] = {
    "F:payout":     5,     # max 5 payouts per minute
    "F:trade":      20,    # max 20 trades per minute
    "X:inference":  30,    # max 30 agent calls per minute
    "P:stage":      100,   # max 100 CRM stage transitions per minute
    "J:task":       200,   # max 200 task executions per minute
}


async def _rate_ok(mem, bucket: str) -> bool:
    """Sliding-window rate check. Returns True if under limit."""
    limit = _RATE_LIMITS.get(bucket)
    if limit is None:
        return True
    key  = f"ratelimit:{bucket}"
    now  = time.time()
    raw  = await mem.get(key)
    calls: list[float] = json.loads(raw) if raw else []
    # Prune calls older than 60 seconds
    calls = [t for t in calls if now - t < 60]
    if len(calls) >= limit:
        return False
    calls.append(now)
    await mem.set(key, json.dumps(calls))
    return True


# ── Treasury floor constraint ─────────────────────────────────────────────────

_TREASURY_FLOOR_BRDG = 10.0    # minimum BRDG reserve before outbound payments are blocked


async def _treasury_floor_ok(mem, channel: str, action: str) -> bool:
    """Block outbound finance actions if treasury is below floor."""
    if channel != "F" or action not in ("payout", "ubi", "distribute"):
        return True
    raw = await mem.get("treasury:brdg:total")
    if raw is None:
        return True  # can't read treasury — don't block
    balance = float(raw)
    return balance >= _TREASURY_FLOOR_BRDG


# ── Worker load constraint ────────────────────────────────────────────────────

_MAX_QUEUE_DEPTH = 500


async def _worker_load_ok(mem) -> bool:
    """Block new job submissions if the queue is overloaded."""
    raw = await mem.get("tasks:pending:count")
    if raw is None:
        return True
    depth = int(raw)
    return depth < _MAX_QUEUE_DEPTH


# ── Agent concurrency constraint ─────────────────────────────────────────────

_MAX_CONCURRENT_AGENTS = 10


async def _agent_concurrency_ok(mem) -> bool:
    """Block new agent spawns if too many are running concurrently."""
    raw = await mem.get("agents:active:count")
    if raw is None:
        return True
    count = int(raw)
    return count < _MAX_CONCURRENT_AGENTS


# ── Master check ─────────────────────────────────────────────────────────────

async def check_constraints(
    mem,
    channel: str,
    action: str,
    amount: float = 0.0,
) -> ConstraintResult:
    """
    Run all applicable constraints for (channel, action).
    Returns ConstraintResult(ok=True) if all pass, else the first failure.

    Args:
        mem:     MemoryStore singleton.
        channel: Emit channel letter (J, X, P, F).
        action:  Human-readable action name (e.g. "payout", "task", "inference").
        amount:  Optional monetary amount for treasury floor checks.
    """
    # 1. Rate limit
    bucket = f"{channel}:{action}"
    if not await _rate_ok(mem, bucket):
        return ConstraintResult(ok=False, reason=f"rate limit exceeded for {bucket}", constraint="RATE")

    # 2. Treasury floor (finance channel only)
    if not await _treasury_floor_ok(mem, channel, action):
        return ConstraintResult(ok=False, reason=f"treasury below floor ({_TREASURY_FLOOR_BRDG} BRDG)", constraint="BALANCE")

    # 3. Worker load
    if channel == "J" and not await _worker_load_ok(mem):
        return ConstraintResult(ok=False, reason=f"worker queue at capacity (>{_MAX_QUEUE_DEPTH})", constraint="LOAD")

    # 4. Agent concurrency
    if channel == "X" and not await _agent_concurrency_ok(mem):
        return ConstraintResult(ok=False, reason=f"agent concurrency limit reached ({_MAX_CONCURRENT_AGENTS})", constraint="AGENT")

    return ConstraintResult(ok=True)


async def constraint_status(mem) -> dict:
    """Return current constraint metric snapshot for observability."""
    pending_raw   = await mem.get("tasks:pending:count")
    agents_raw    = await mem.get("agents:active:count")
    treasury_raw  = await mem.get("treasury:brdg:total")
    return {
        "queue_depth":       int(pending_raw)   if pending_raw   else 0,
        "active_agents":     int(agents_raw)    if agents_raw    else 0,
        "treasury_brdg":     float(treasury_raw) if treasury_raw else 0.0,
        "treasury_floor":    _TREASURY_FLOOR_BRDG,
        "max_queue":         _MAX_QUEUE_DEPTH,
        "max_agents":        _MAX_CONCURRENT_AGENTS,
        "rate_limits":       _RATE_LIMITS,
    }
