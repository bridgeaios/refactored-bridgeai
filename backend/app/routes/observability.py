"""
observability.py — Gaps 18, 22, 23, 24: Deep Observability, Network Topology,
                   Incentive Alignment, and API Boundary Layer.

Endpoints (all require JWT):
  GET  /observe/health          — system health + constraint status
  GET  /observe/clock           — current cycle, window, settlement status
  GET  /observe/costs           — cost accounting summary (current cycle)
  GET  /observe/costs/recent    — last N cost entries
  GET  /observe/agents          — live agent registry
  GET  /observe/dlq             — dead-letter queue contents
  GET  /observe/audit           — recent audit trail entries
  GET  /observe/topology        — network topology graph (nodes + edges)
  GET  /observe/incentives      — incentive alignment model snapshot
  POST /observe/dlq/{key}/retry — re-queue a DLQ entry
  GET  /observe/summary         — full system summary (all above, one call)
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends

from app.domains.infra.deps import require_jwt

router = APIRouter(prefix="/observe", tags=["observability"])


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    from app.core.deps import get_memory
    from app.core.constraints import check_constraints, constraint_status
    mem = get_memory()
    constraints = await constraint_status(mem)
    return {
        "status": "ok",
        "ts": time.time(),
        "constraints": constraints,
    }


# ── Clock / Time System ────────────────────────────────────────────────────────

@router.get("/clock")
async def clock_info(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 13: Current cycle, window, settlement status."""
    from app.core.clock import cycle_info
    return cycle_info()


# ── Cost Accounting ────────────────────────────────────────────────────────────

@router.get("/costs")
async def cost_summary_endpoint(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 14: Per-channel cost totals for the current cycle."""
    from app.core.deps import get_memory
    from app.core.cost import cost_summary
    mem = get_memory()
    return await cost_summary(mem)


@router.get("/costs/recent")
async def cost_recent_endpoint(limit: int = 50, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 14: Most recent cost entries (default last 50)."""
    from app.core.deps import get_memory
    from app.core.cost import cost_recent
    mem = get_memory()
    entries = await cost_recent(mem, limit=min(limit, 200))
    return {"entries": entries, "count": len(entries)}


# ── Agent Lifecycle ────────────────────────────────────────────────────────────

@router.get("/agents")
async def agent_registry_endpoint(include_retired: bool = False, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 19: Live agent registry with status (active/idle/retired)."""
    from app.core.deps import get_memory
    from app.core.lifecycle import agent_registry, agent_count
    mem = get_memory()
    agents = await agent_registry(mem, include_retired=include_retired)
    counts = await agent_count(mem)
    return {"agents": agents, "counts": counts, "ts": time.time()}


# ── Dead-Letter Queue ──────────────────────────────────────────────────────────

@router.get("/dlq")
async def dlq_list_endpoint(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 12: Dead-letter queue — failed operations that exceeded MAX_RETRIES."""
    from app.core.deps import get_memory
    from app.core.idempotency import dlq_list
    mem = get_memory()
    entries = await dlq_list(mem)
    return {"entries": entries, "count": len(entries)}


@router.post("/dlq/{key}/retry")
async def dlq_retry_endpoint(key: str, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 12: Re-queue a DLQ entry for retry."""
    from app.core.deps import get_memory
    from app.core.idempotency import dlq_retry
    mem = get_memory()
    ok = await dlq_retry(mem, key)
    return {"ok": ok, "key": key}


# ── Audit Trail ────────────────────────────────────────────────────────────────

@router.get("/audit")
async def audit_log_endpoint(limit: int = 100, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 25: Recent audit trail entries."""
    from app.core.deps import get_memory
    from app.core.compliance import audit_recent, compliance_status
    mem = get_memory()
    entries = await audit_recent(mem, limit=min(limit, 500))
    status = await compliance_status(mem)
    return {"entries": entries, "compliance": status, "ts": time.time()}


# ── Network Topology ────────────────────────────────────────────────────────────

@router.get("/topology")
async def network_topology(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """
    Gap 22: Network topology graph.

    Returns nodes (system components) and edges (data flows) as a graph structure
    suitable for D3.js / Cytoscape rendering.
    """
    nodes = [
        {"id": "gateway",      "label": "API Gateway",    "layer": "boundary",  "channel": None},
        {"id": "crm",          "label": "CRM",            "layer": "pipeline",  "channel": "P"},
        {"id": "outreach",     "label": "Outreach",       "layer": "pipeline",  "channel": "P"},
        {"id": "billing",      "label": "Billing",        "layer": "finance",   "channel": "F"},
        {"id": "treasury",     "label": "Treasury",       "layer": "finance",   "channel": "F"},
        {"id": "marketplace",  "label": "Marketplace",    "layer": "jobs",      "channel": "J"},
        {"id": "workers",      "label": "Workers",        "layer": "jobs",      "channel": "J"},
        {"id": "osint",        "label": "OSINT Agent",    "layer": "agents",    "channel": "X"},
        {"id": "emit_gate",    "label": "Emit Gate",      "layer": "control",   "channel": None},
        {"id": "event_bus",    "label": "Event Bus",      "layer": "control",   "channel": None},
        {"id": "controlplane", "label": "Control Plane",  "layer": "control",   "channel": None},
        {"id": "memory",       "label": "MemoryStore",    "layer": "storage",   "channel": None},
    ]

    edges = [
        {"source": "gateway",     "target": "emit_gate",    "label": "all requests"},
        {"source": "emit_gate",   "target": "crm",          "label": "P-gated"},
        {"source": "emit_gate",   "target": "billing",      "label": "F-gated"},
        {"source": "emit_gate",   "target": "marketplace",  "label": "J-gated"},
        {"source": "emit_gate",   "target": "workers",      "label": "J-gated"},
        {"source": "crm",         "target": "outreach",     "label": "stage→email"},
        {"source": "crm",         "target": "osint",        "label": "enrich lead"},
        {"source": "outreach",    "target": "billing",      "label": "invoice trigger"},
        {"source": "billing",     "target": "treasury",     "label": "collect payment"},
        {"source": "marketplace", "target": "workers",      "label": "task dispatch"},
        {"source": "workers",     "target": "osint",        "label": "spawn agent"},
        {"source": "workers",     "target": "event_bus",    "label": "emit events"},
        {"source": "event_bus",   "target": "controlplane", "label": "stream"},
        {"source": "treasury",    "target": "memory",       "label": "ledger write"},
        {"source": "workers",     "target": "memory",       "label": "state read/write"},
    ]

    return {"nodes": nodes, "edges": edges, "ts": time.time()}


# ── Incentive Alignment ────────────────────────────────────────────────────────

@router.get("/incentives")
async def incentive_model(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """
    Gap 23: Incentive alignment model snapshot.

    Returns the current incentive structure — how value flows from actions
    to rewards, and the penalty/reward balance at each layer.
    """
    from app.core.deps import get_memory
    from app.core.cost import cost_summary
    from app.core.clock import cycle_info
    mem = get_memory()
    costs = await cost_summary(mem)
    clock = cycle_info()

    # Treasury split model
    treasury_split = {
        "ubi":     {"pct": 40, "description": "Universal Basic Income — all registered nodes"},
        "reserve": {"pct": 30, "description": "Treasury reserve — system stability buffer"},
        "ops":     {"pct": 20, "description": "Operational costs — infra, workers, APIs"},
        "founder": {"pct": 10, "description": "Founder allocation — product development"},
    }

    # Emit channel value weights
    channel_weights = {
        "J": {"label": "Job",      "base_value": 1.0, "cost_floor": 0.1,  "incentive": "throughput"},
        "X": {"label": "Agent",    "base_value": 1.0, "cost_floor": 0.05, "incentive": "discovery"},
        "P": {"label": "Pipeline", "base_value": 1.0, "cost_floor": 0.3,  "incentive": "conversion"},
        "F": {"label": "Finance",  "base_value": 1.0, "cost_floor": 0.01, "incentive": "yield"},
    }

    return {
        "treasury_split":   treasury_split,
        "channel_weights":  channel_weights,
        "cost_headroom":    costs.get("headroom", {}),
        "cycle":            clock.get("cycle"),
        "window":           clock.get("window"),
        "settling":         clock.get("settling"),
        "ts":               time.time(),
    }


# ── Full Summary ───────────────────────────────────────────────────────────────

@router.get("/summary")
async def full_summary(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Gap 24: Single-call API boundary — all system metrics in one response."""
    from app.core.deps import get_memory
    from app.core.clock import cycle_info
    from app.core.cost import cost_summary
    from app.core.constraints import constraint_status
    from app.core.lifecycle import agent_count
    from app.core.idempotency import dlq_list
    from app.core.compliance import compliance_status

    mem = get_memory()

    # Gather all in parallel would require asyncio.gather —
    # using sequential for simplicity (all are fast mem reads)
    return {
        "clock":       cycle_info(),
        "costs":       await cost_summary(mem),
        "constraints": await constraint_status(mem),
        "agents":      await agent_count(mem),
        "dlq_count":   len(await dlq_list(mem)),
        "compliance":  await compliance_status(mem),
        "ts":          time.time(),
    }
