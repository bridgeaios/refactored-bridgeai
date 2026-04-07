"""
AOE-RUNTIME REST API v2
All process management flows through here.
Terminal is a display layer only -- actual work happens here.

Ported from BRIDGE_AI_OS/core/app/routes/runtime.py.

Endpoints:
  GET  /runtime/services                    -- list all
  GET  /runtime/services/{name}             -- single status
  POST /runtime/services/{name}/start
  POST /runtime/services/{name}/stop
  POST /runtime/services/{name}/restart
  POST /runtime/services/{name}/unlock      -- clear FAILED_LOCKED
  GET  /runtime/services/{name}/logs        -- disk log tail
  GET  /runtime/health                      -- 3-level health all running
  GET  /runtime/conflicts                   -- port conflict scan
  POST /runtime/consolidate                 -- phase-gated startup
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.domains.runtime.manager import get_manager

router = APIRouter(prefix="/runtime", tags=["runtime"])


# ── Service listing ────────────────────────────────────────────────────────────

@router.get("/services")
async def list_services() -> dict[str, Any]:
    return {"services": get_manager().list_services()}


@router.get("/services/{name}")
async def get_service(name: str) -> dict[str, Any]:
    result = get_manager().status(name)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not found"))
    return result


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@router.post("/services/{name}/start")
async def start_service(name: str) -> dict[str, Any]:
    result = await get_manager().start(name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/services/{name}/stop")
async def stop_service(name: str) -> dict[str, Any]:
    result = await get_manager().stop(name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/services/{name}/restart")
async def restart_service(name: str) -> dict[str, Any]:
    result = await get_manager().restart(name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/services/{name}/unlock")
async def unlock_service(name: str) -> dict[str, Any]:
    """Clear FAILED_LOCKED state after a restart storm."""
    result = get_manager().unlock(name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/services/{name}/logs")
async def get_logs(name: str, lines: int = Query(default=100, le=2000)) -> dict[str, Any]:
    """
    Returns last N lines from disk log (logs/{name}.log).
    Falls back to in-memory ring buffer.
    """
    log_lines = get_manager().logs(name, lines=lines)
    return {"name": name, "lines": log_lines, "count": len(log_lines)}


# ── Health & diagnostics ──────────────────────────────────────────────────────

@router.get("/health")
async def health_all() -> dict[str, Any]:
    """3-level health check (process + port + HTTP endpoint) for all services."""
    mgr      = get_manager()
    services = mgr.list_services()
    results  = []
    for svc in services:
        h = mgr.health_check(svc["name"])
        results.append({**svc, **h})
    return {"services": results}


@router.get("/conflicts")
async def port_conflicts() -> dict[str, Any]:
    """Scan service definitions for port collisions."""
    return {"conflicts": get_manager().scan_conflicts()}


# ── Consolidation engine ──────────────────────────────────────────────────────

@router.post("/consolidate")
async def run_consolidation() -> dict[str, Any]:
    """
    Phase-gated startup following consolidation_phases in services.json.
    Blocks on first failed phase.
    """
    results = await get_manager().run_consolidation()
    all_ok  = all(r["ok"] for r in results)
    return {"ok": all_ok, "phases": results}
