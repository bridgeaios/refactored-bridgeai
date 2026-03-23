"""
CLI Orchestration — deterministic, logged command runner queue.

Security model:
- The backend NEVER executes OS commands.
- It only stores jobs and receives execution reports.
- A separate local runner process (node script) polls /api/cli/queue and executes
  allowlisted commands, posting results back to /api/cli/report.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.runtime import memory

router = APIRouter()

QUEUE_KEY = "cli:queue"
HISTORY_KEY = "cli:history"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def _env_bool(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _cli_enabled() -> tuple[bool, str]:
    # Conservative default: disabled unless explicitly enabled in local/dev.
    env = (os.getenv("ENV") or os.getenv("NODE_ENV") or "").strip().lower()
    if env == "local":
        return True, "env_local"
    if _env_bool("BRIDGE_ALLOW_CLI_RUNNER"):
        return True, "allow_flag"
    return False, "disabled"


async def _load_queue() -> list[dict[str, Any]]:
    raw = await memory.get(QUEUE_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _save_queue(q: list[dict[str, Any]]) -> None:
    await memory.set(QUEUE_KEY, json.dumps(q))


@router.get("/cli/status")
async def cli_status():
    enabled, reason = _cli_enabled()
    return {
        "ok": True,
        "enabled": enabled,
        "mode": reason,
        "observed_env": {
            "ENV": os.getenv("ENV"),
            "NODE_ENV": os.getenv("NODE_ENV"),
            "BRIDGE_ALLOW_CLI_RUNNER": os.getenv("BRIDGE_ALLOW_CLI_RUNNER"),
        },
    }


@router.post("/cli/enqueue")
async def cli_enqueue(payload: dict, request: Request):
    enabled, reason = _cli_enabled()
    if not enabled:
        raise HTTPException(status_code=403, detail=f"cli runner disabled ({reason})")

    cmd_id = (payload.get("cmd_id") or "").strip()
    args = payload.get("args")
    if args is None:
        args = []
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise HTTPException(status_code=400, detail="args must be a list[str]")

    if not cmd_id:
        raise HTTPException(status_code=400, detail="cmd_id required")

    # Deterministic-ish id: hash of cmd + args + timestamp seconds.
    base = f"{cmd_id}::{json.dumps(args, ensure_ascii=False)}::{int(time.time())}"
    job_id = "job_" + _sha(base)[:16]

    job: dict[str, Any] = {
        "id": job_id,
        "created_at": _now(),
        "created_by": request.headers.get("X-User-Id") or request.client.host if request.client else "unknown",
        "cmd_id": cmd_id,
        "args": args,
        "status": "queued",  # queued|running|done|failed
        "runner_id": None,
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
        "stdout": None,
        "stderr": None,
    }
    q = await _load_queue()
    q.append(job)
    # cap queue length
    if len(q) > 200:
        q = q[-200:]
    await _save_queue(q)
    return {"ok": True, "job": job}


@router.get("/cli/queue/next")
async def cli_queue_next(runner_id: str = "runner"):
    enabled, reason = _cli_enabled()
    if not enabled:
        raise HTTPException(status_code=403, detail=f"cli runner disabled ({reason})")

    q = await _load_queue()
    for job in q:
        if job.get("status") == "queued":
            job["status"] = "running"
            job["runner_id"] = runner_id
            job["started_at"] = _now()
            await _save_queue(q)
            return {"ok": True, "job": job}
    return {"ok": True, "job": None}


@router.post("/cli/report")
async def cli_report(payload: dict):
    enabled, _ = _cli_enabled()
    if not enabled:
        # accept reports even if disabled, to allow runner shutdown reporting
        pass
    job_id = (payload.get("id") or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="id required")

    q = await _load_queue()
    updated = None
    for job in q:
        if job.get("id") == job_id:
            job["status"] = payload.get("status") or job.get("status")
            job["finished_at"] = payload.get("finished_at") or _now()
            job["exit_code"] = payload.get("exit_code")
            job["stdout"] = payload.get("stdout")
            job["stderr"] = payload.get("stderr")
            updated = job
            break
    if updated is None:
        raise HTTPException(status_code=404, detail="job not found")
    await _save_queue(q)
    # append to history (bounded)
    await memory.append(HISTORY_KEY, updated)
    return {"ok": True, "job": updated}


@router.get("/cli/history")
async def cli_history(limit: int = 30):
    limit = max(1, min(int(limit), 200))
    items = await memory.get_recent(HISTORY_KEY, limit)
    return {"ok": True, "count": len(items), "items": list(reversed(items))}

