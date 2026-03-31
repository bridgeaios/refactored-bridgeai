"""
emit.py — Binary execution gate (Invoke-Emit, Python implementation).

Every action, task, revenue path, or agent call passes through emit().
Only value-positive executions survive. Everything else → None (silence).

Usage:
    from app.core.emit import emit, Channel

    if emit(Channel.PIPELINE, values=[score, deal_value], cost=acquisition_cost):
        lead.stage = "qualified"

    if emit(Channel.FINANCE, values=[expected_return], cost=risk_cost):
        await treasury.collect(...)

    if emit(Channel.AGENT, values=[impact_score], cost=compute_cost):
        await run_agent()
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Sequence

log = logging.getLogger(__name__)

# ── Channel taxonomy (Θ — valid message types) ─────────────────────────────
class Channel(str, Enum):
    FINANCE  = "F"   # treasury, payouts, capital deployment
    PIPELINE = "P"   # CRM stage transitions, lead qualification
    JOB      = "J"   # task queue, worker jobs
    AGENT    = "X"   # AI agent decisions, inference cycles

# All valid channels (Θ)
_THETA: frozenset[str] = frozenset(c.value for c in Channel)


def emit(
    channel: Channel | str,
    values: Sequence[float],
    cost: float,
    *,
    log_silenced: bool = False,
) -> bool:
    """
    Binary execution gate: returns True iff the action is value-positive.

    Args:
        channel:      The execution channel (must be in Θ).
        values:       List of value components (p_i). Summed for V.
        cost:         Execution cost (c). Subtracted from V.
        log_silenced: If True, log silenced calls at DEBUG level.

    Returns:
        True  → execute (V > 0 and channel ∈ Θ)
        False → silence (drop the action, no side-effects)

    Mathematical definition:
        V = Σ(values) − cost
        emit = 1  iff  channel ∈ Θ  ∧  V > 0
               ∅  otherwise
    """
    # Validate channel membership (M ⊆ Θ)
    ch_val = channel.value if isinstance(channel, Channel) else str(channel)
    if ch_val not in _THETA:
        if log_silenced:
            log.debug("[EMIT] SILENCED — unknown channel %r", ch_val)
        return False

    # Value function: V = Σ(p) − c
    v = sum(values) - cost

    if v > 0:
        return True

    if log_silenced:
        log.debug("[EMIT] SILENCED — channel=%s V=%.4f (values=%s cost=%.4f)", ch_val, v, values, cost)
    return False


# ── Typed convenience wrappers ──────────────────────────────────────────────

def emit_finance(values: Sequence[float], cost: float = 0.0) -> bool:
    """Gate treasury operations, payouts, capital deployment."""
    return emit(Channel.FINANCE, values, cost)


def emit_pipeline(values: Sequence[float], cost: float = 0.0) -> bool:
    """Gate CRM stage transitions and lead promotions."""
    return emit(Channel.PIPELINE, values, cost)


def emit_job(values: Sequence[float], cost: float = 0.0) -> bool:
    """Gate task queue execution."""
    return emit(Channel.JOB, values, cost)


def emit_agent(values: Sequence[float], cost: float = 0.0) -> bool:
    """Gate AI agent decisions and inference cycles."""
    return emit(Channel.AGENT, values, cost)


# ── Standardized response format ────────────────────────────────────────────

def emit_response(label: str, values: Sequence[float], cost: float) -> dict:
    """
    Build a standardized emit-aware response payload.

    The global EmitGateMiddleware reads the ``net`` field from every JSON
    response body. If net ≤ 0 the middleware silences the response with 204.

    Args:
        label:  Human-readable action label.
        values: Value components (p_i).
        cost:   Execution cost.

    Returns:
        dict with keys: label, values, cost, net, pass
    """
    net = sum(values) - cost
    return {
        "label": label,
        "values": list(values),
        "cost": cost,
        "net": round(net, 6),
        "pass": net > 0,
    }
