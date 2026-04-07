"""
bridgeos.tvm — Topic Vector Matrix HTTP API.

Mounted at ``/api/tvm`` (manifest base_path ``/tvm`` under API prefix).

Static paths are registered **before** ``/{topic}`` so ``events`` is not captured as a topic.
"""
from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domains.tvm import events as tvm_events
from app.domains.tvm import store as tvm_store
from app.domains.tvm.deps import get_tvm_principal, require_any_role
from app.domains.tvm.models import (
    ExecutorResultBody,
    TVMApprovalBody,
    TVMPrincipal,
    TVMProposalBody,
    TVMRow,
)
from app.domains.tvm.signing import sign_row, verify_row
from app.domains.tvm.store import RECOMMENDATION_LIB

router = APIRouter(prefix="/tvm", tags=["bridgeos.tvm"])

Principal = Annotated[TVMPrincipal, Depends(get_tvm_principal)]


def _sign_and_put(row: dict[str, Any]) -> dict[str, Any]:
    row["last_updated"] = int(time.time())
    row["signature"] = sign_row(row)
    return tvm_store.put_row(row)


def _publish_map_node(row: dict[str, Any]) -> None:
    tvm_events.publish(
        "map.updated",
        {
            "nodes": [
                {
                    "id": row["topic"],
                    "status": "healthy" if row.get("healthy") else "unhealthy",
                    "action_required": bool(row.get("action_required")),
                    "autofix_available": bool(row.get("autofix_available")),
                }
            ],
        },
    )


@router.get("", response_model=list[TVMRow])
async def get_all_rows(principal: Principal) -> list[TVMRow]:
    require_any_role(principal, ["tvm.reader", "tvm.operator", "tvm.agent", "tvm.system"])
    return [TVMRow.model_validate(r) for r in tvm_store.get_all_rows()]


@router.get("/events/recent")
async def get_recent_events(
    principal: Principal,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    require_any_role(principal, ["tvm.operator", "tvm.system"])
    return {"ok": True, "items": tvm_events.recent(limit)}


@router.get("/meta/signature/{topic}")
async def verify_signature(topic: str, principal: Principal) -> dict[str, Any]:
    """Verify stored row HMAC (reader+)."""
    require_any_role(principal, ["tvm.reader", "tvm.operator", "tvm.agent", "tvm.system"])
    raw = tvm_store.get_row(topic)
    if not raw:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"ok": True, "valid": verify_row(raw), "topic": topic}


@router.get("/{topic}", response_model=TVMRow)
async def get_row(topic: str, principal: Principal) -> TVMRow:
    require_any_role(principal, ["tvm.reader", "tvm.operator", "tvm.agent", "tvm.system"])
    raw = tvm_store.get_row(topic)
    if not raw:
        raise HTTPException(status_code=404, detail="Topic not found")
    return TVMRow.model_validate(raw)


@router.post("/{topic}", response_model=TVMRow)
async def upsert_row(topic: str, payload: TVMRow, principal: Principal) -> TVMRow:
    """Create or replace full row (operator/system). Manifest: POST /{topic} UpdateRow."""
    require_any_role(principal, ["tvm.operator", "tvm.system"])
    if payload.topic != topic:
        raise HTTPException(status_code=400, detail="Body topic must match path")
    prev = tvm_store.get_row(topic)
    row = payload.model_dump()
    row = _sign_and_put(row)
    tvm_events.publish(
        "tvm.updated",
        {
            "topic": topic,
            "previous": {k: prev.get(k) for k in ("healthy", "degraded", "action_required", "recommendation_code")}
            if prev
            else {},
            "current": {
                "healthy": row.get("healthy"),
                "degraded": row.get("degraded"),
                "action_required": row.get("action_required"),
                "recommendation_code": row.get("recommendation_code"),
            },
            "changed_by_role": next((r for r in principal.roles if r.startswith("tvm.")), "unknown"),
        },
    )
    _publish_map_node(row)
    return TVMRow.model_validate(row)


@router.post("/{topic}/proposal", response_model=TVMRow)
async def propose_recommendation(topic: str, body: TVMProposalBody, principal: Principal) -> TVMRow:
    require_any_role(principal, ["tvm.agent"])
    raw = tvm_store.get_row(topic)
    if not raw:
        raise HTTPException(status_code=404, detail="Topic not found")
    if body.recommendation_code not in RECOMMENDATION_LIB:
        raise HTTPException(status_code=400, detail="Unknown recommendation_code")
    meta = RECOMMENDATION_LIB[body.recommendation_code]
    prev = dict(raw)
    raw["recommendation_code"] = body.recommendation_code
    raw["action_required"] = 1
    raw["human_approval_needed"] = 1 if meta.get("requires_human_approval") else 0
    raw = _sign_and_put(raw)
    tvm_events.publish(
        "observer.request",
        {
            "topic": topic,
            "tvm_snapshot": raw,
            "correlation_id": f"{topic}-obs",
        },
    )
    tvm_events.publish(
        "tvm.updated",
        {
            "topic": topic,
            "previous": {k: prev.get(k) for k in ("healthy", "degraded", "action_required", "recommendation_code")},
            "current": {
                "healthy": raw.get("healthy"),
                "degraded": raw.get("degraded"),
                "action_required": raw.get("action_required"),
                "recommendation_code": raw.get("recommendation_code"),
            },
            "changed_by_role": "tvm.agent",
        },
    )
    if not raw.get("human_approval_needed"):
        tvm_events.publish(
            "executor.request",
            {
                "topic": topic,
                "recommendation_code": body.recommendation_code,
                "steps": meta.get("steps", []),
                "requires_human_approval": False,
                "correlation_id": f"{topic}-exe",
            },
        )
    return TVMRow.model_validate(raw)


@router.post("/{topic}/approval", response_model=TVMRow)
async def approve_recommendation(topic: str, body: TVMApprovalBody, principal: Principal) -> TVMRow:
    require_any_role(principal, ["tvm.operator"])
    raw = tvm_store.get_row(topic)
    if not raw:
        raise HTTPException(status_code=404, detail="Topic not found")
    if not raw.get("recommendation_code"):
        raise HTTPException(status_code=400, detail="No recommendation to approve")
    prev = dict(raw)
    if not body.approve:
        raw["recommendation_code"] = None
        raw["action_required"] = 0
        raw["human_approval_needed"] = 0
    else:
        raw["human_approval_needed"] = 0
        raw["action_required"] = 1
    raw = _sign_and_put(raw)
    tvm_events.publish(
        "tvm.updated",
        {
            "topic": topic,
            "previous": {k: prev.get(k) for k in ("healthy", "degraded", "action_required", "recommendation_code")},
            "current": {
                "healthy": raw.get("healthy"),
                "degraded": raw.get("degraded"),
                "action_required": raw.get("action_required"),
                "recommendation_code": raw.get("recommendation_code"),
            },
            "changed_by_role": "tvm.operator",
        },
    )
    if body.approve and raw.get("recommendation_code"):
        code = str(raw["recommendation_code"])
        meta = RECOMMENDATION_LIB.get(code, {})
        tvm_events.publish(
            "executor.request",
            {
                "topic": topic,
                "recommendation_code": code,
                "steps": meta.get("steps", []),
                "requires_human_approval": False,
                "correlation_id": f"{topic}-exe-appr",
            },
        )
    return TVMRow.model_validate(raw)


@router.post("/{topic}/executor-result", response_model=TVMRow)
async def post_executor_result(topic: str, body: ExecutorResultBody, principal: Principal) -> TVMRow:
    """Executor posts outcome; TVM updates health bits when status is success."""
    require_any_role(principal, ["tvm.executor", "tvm.system"])
    raw = tvm_store.get_row(topic)
    if not raw:
        raise HTTPException(status_code=404, detail="Topic not found")
    prev = dict(raw)
    tvm_events.publish(
        "executor.result",
        {
            "topic": topic,
            "recommendation_code": body.recommendation_code,
            "status": body.status,
            "details": body.details,
            "new_health": body.new_health,
            "new_degraded": body.new_degraded,
            "correlation_id": body.correlation_id,
            "emitted_at": body.emitted_at or int(time.time()),
        },
    )
    if body.status == "success":
        raw["healthy"] = body.new_health
        raw["degraded"] = body.new_degraded
        raw["action_required"] = 0
        raw["recommendation_code"] = None
        raw["human_approval_needed"] = 0
    raw = _sign_and_put(raw)
    tvm_events.publish(
        "tvm.updated",
        {
            "topic": topic,
            "previous": {k: prev.get(k) for k in ("healthy", "degraded", "action_required", "recommendation_code")},
            "current": {
                "healthy": raw.get("healthy"),
                "degraded": raw.get("degraded"),
                "action_required": raw.get("action_required"),
                "recommendation_code": raw.get("recommendation_code"),
            },
            "changed_by_role": "tvm.executor" if "tvm.executor" in principal.roles else "tvm.system",
        },
    )
    _publish_map_node(raw)
    return TVMRow.model_validate(raw)
