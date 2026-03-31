"""
Control Plane router — live topology, event stream, admin overrides.

Endpoints:
  GET  /api/control/topology        — node health snapshot (JSON)
  GET  /api/control/events          — SSE stream of activation loop events
  POST /api/control/trigger/{action} — admin override actions
  GET  /api/control/metrics         — real-time metrics (treasury, leads, trades, workers)

All endpoints require JWT or BRIDGE_INTERNAL_TOKEN.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.domains.infra.deps import require_jwt

router = APIRouter(prefix="/control", tags=["control-plane"])

# ─────────────────────────────────────────────────────────────
# In-process event bus: activation loop and workers write here;
# SSE clients read from it. Kept small — last 200 events.
# ─────────────────────────────────────────────────────────────
_event_log: list[dict] = []
_event_listeners: list[asyncio.Queue] = []
_MAX_LOG = 200


def emit_event(type_: str, data: dict) -> None:
    """Push an event onto the in-process bus. Called by workers / activation loop."""
    entry = {"type": type_, "data": data, "ts": time.time()}
    _event_log.append(entry)
    if len(_event_log) > _MAX_LOG:
        _event_log.pop(0)
    for q in list(_event_listeners):
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass


# ─────────────────────────────────────────────────────────────
# GET /control/topology
# ─────────────────────────────────────────────────────────────

@router.get("/topology")
async def topology(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Return health status of each system node."""
    from app.core.deps import get_memory

    mem = get_memory()
    nodes: list[dict] = []

    # CRM
    try:
        from app.domains.crm.deps import get_crm
        stats = await get_crm().stats()
        nodes.append({
            "id": "crm", "label": "CRM", "status": "ok",
            "meta": {"total_leads": stats.get("total_leads", 0),
                     "stages": stats.get("by_stage", {})},
        })
    except Exception as e:
        nodes.append({"id": "crm", "label": "CRM", "status": "error", "meta": {"error": str(e)[:80]}})

    # Billing
    try:
        from app.domains.billing.deps import get_billing
        inv_stats = await get_billing().stats()
        nodes.append({
            "id": "billing", "label": "Billing", "status": "ok",
            "meta": inv_stats,
        })
    except Exception as e:
        nodes.append({"id": "billing", "label": "Billing", "status": "error", "meta": {"error": str(e)[:80]}})

    # Outreach
    try:
        from app.domains.outreach.deps import get_outreach
        ostat = await get_outreach().stats()
        nodes.append({
            "id": "outreach", "label": "Outreach", "status": "ok",
            "meta": ostat,
        })
    except Exception as e:
        nodes.append({"id": "outreach", "label": "Outreach", "status": "error", "meta": {"error": str(e)[:80]}})

    # Treasury
    try:
        from app.services.treasury import TreasuryService
        ts = await TreasuryService(mem).get_status()
        nodes.append({
            "id": "treasury", "label": "Treasury", "status": "ok",
            "meta": {"brdg": round(ts.get("total_brdg", 0), 6),
                     "zar": round(ts.get("total_zar", 0), 2)},
        })
    except Exception as e:
        nodes.append({"id": "treasury", "label": "Treasury", "status": "error", "meta": {"error": str(e)[:80]}})

    # Economy / Network
    try:
        from app.domains.economy.deps import get_economy
        enodes = await get_economy().list_nodes() if hasattr(get_economy(), "list_nodes") else []
        nodes.append({
            "id": "economy", "label": "Economy", "status": "ok",
            "meta": {"network_nodes": len(enodes)},
        })
    except Exception as e:
        nodes.append({"id": "economy", "label": "Economy", "status": "degraded", "meta": {"error": str(e)[:80]}})

    # Worker health — last heartbeat timestamp
    last_hb = await mem.get("worker:last_heartbeat")
    worker_status = "ok"
    if last_hb:
        age = time.time() - float(last_hb)
        worker_status = "ok" if age < 30 else ("degraded" if age < 120 else "error")
    else:
        worker_status = "unknown"
    nodes.append({
        "id": "workers", "label": "Workers", "status": worker_status,
        "meta": {"last_heartbeat": last_hb},
    })

    # Activation loop — last run timestamp
    last_loop = await mem.get("activation_loop:last_run")
    loop_status = "ok" if last_loop and (time.time() - float(last_loop)) < 30 else "idle"
    nodes.append({
        "id": "activation_loop", "label": "Activation Loop", "status": loop_status,
        "meta": {"last_run": last_loop},
    })

    return {"nodes": nodes, "ts": time.time()}


# ─────────────────────────────────────────────────────────────
# GET /control/metrics
# ─────────────────────────────────────────────────────────────

@router.get("/metrics")
async def metrics(_: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Real-time metrics snapshot."""
    from app.core.deps import get_memory
    mem = get_memory()

    treasury_brdg = 0.0
    try:
        from app.services.treasury import TreasuryService
        ts = await TreasuryService(mem).get_status()
        treasury_brdg = round(ts.get("total_brdg", 0), 6)
    except Exception:
        pass

    lead_count = 0
    pipeline: dict = {}
    try:
        from app.domains.crm.deps import get_crm
        stats = await get_crm().stats()
        lead_count = stats.get("total_leads", 0)
        pipeline = stats.get("by_stage", {})
    except Exception:
        pass

    outreach_pending = 0
    try:
        from app.domains.outreach.deps import get_outreach
        ostat = await get_outreach().stats()
        outreach_pending = ostat.get("by_status", {}).get("pending", 0)
    except Exception:
        pass

    trade_count = 0
    try:
        from app.services.treasury import TreasuryService
        ledger = await TreasuryService(mem).get_ledger(limit=500)
        trade_count = sum(1 for e in ledger if e.get("method") == "trade")
    except Exception:
        pass

    # Hourly task telemetry
    task_buckets: list = await mem.get("telemetry:hourly:tasks") or []
    task_labels: list = await mem.get("telemetry:hourly:labels") or []

    # Recent event log
    recent_events = _event_log[-50:]

    return {
        "treasury_brdg": treasury_brdg,
        "leads": lead_count,
        "pipeline": pipeline,
        "outreach_pending": outreach_pending,
        "trades": trade_count,
        "task_buckets": task_buckets,
        "task_labels": task_labels,
        "event_count": len(_event_log),
        "recent_events": recent_events,
        "ts": time.time(),
    }


# ─────────────────────────────────────────────────────────────
# GET /control/events  — SSE stream
# ─────────────────────────────────────────────────────────────

@router.get("/events")
async def event_stream(_: dict = Depends(require_jwt)) -> StreamingResponse:
    """Server-Sent Events stream of activation loop and system events."""
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _sse_generator() -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _event_listeners.append(q)

    # Replay last 20 events on connect
    for entry in _event_log[-20:]:
        yield _sse_format(entry)

    try:
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=20.0)
                yield _sse_format(entry)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        try:
            _event_listeners.remove(q)
        except ValueError:
            pass


def _sse_format(entry: dict) -> str:
    return f"data: {json.dumps(entry)}\n\n"


# ─────────────────────────────────────────────────────────────
# POST /control/trigger/{action}  — admin overrides
# ─────────────────────────────────────────────────────────────

_ALLOWED_ACTIONS = {
    "activation_loop", "flag_overdue", "clear_outreach_queue",
    "score_refresh", "security_check",
}


@router.post("/trigger/{action}")
async def trigger_action(action: str, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Admin override: trigger a system action immediately."""
    if action not in _ALLOWED_ACTIONS:
        from fastapi import HTTPException
        raise HTTPException(400, detail=f"Unknown action '{action}'. Allowed: {sorted(_ALLOWED_ACTIONS)}")

    from app.core.deps import get_memory
    mem = get_memory()
    result: dict[str, Any] = {"action": action, "status": "ok"}

    if action == "activation_loop":
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
        from workers import _activation_loop
        asyncio.ensure_future(_activation_loop(mem))
        emit_event("admin_override", {"action": "activation_loop", "note": "manual trigger"})
        result["note"] = "activation loop cycle queued"

    elif action == "flag_overdue":
        from app.domains.billing.deps import get_billing
        billing = get_billing()
        flagged = await billing.flag_overdue() if hasattr(billing, "flag_overdue") else []
        emit_event("admin_override", {"action": "flag_overdue", "flagged": len(flagged) if isinstance(flagged, list) else 0})
        result["flagged"] = len(flagged) if isinstance(flagged, list) else 0

    elif action == "clear_outreach_queue":
        from app.domains.outreach.deps import get_outreach
        outreach = get_outreach()
        if hasattr(outreach, "clear_queue"):
            cleared = await outreach.clear_queue()
        else:
            cleared = 0
        emit_event("admin_override", {"action": "clear_outreach_queue", "cleared": cleared})
        result["cleared"] = cleared

    elif action == "score_refresh":
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
        from workers import _brain_process
        asyncio.ensure_future(_brain_process(mem))
        emit_event("admin_override", {"action": "score_refresh", "note": "brain process queued"})
        result["note"] = "brain process queued"

    elif action == "security_check":
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
        from workers import _security_check
        asyncio.ensure_future(_security_check(mem))
        emit_event("admin_override", {"action": "security_check", "note": "security check queued"})
        result["note"] = "security check queued"

    return result
