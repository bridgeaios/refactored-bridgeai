"""
Economy domain router.

Replaces economy-related endpoints previously scattered across:
  - routes/api.py  (marketplace, ubi, revenue endpoints)
  - routes/treasury.py  (treasury endpoints)

All endpoints preserved at identical paths. No breaking changes.
"""
from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.economy.deps import get_economy
from app.domains.infra.deps import require_jwt
from app.domains.economy.models import (
    AcceptTaskRequest,
    CollectRequest,
    CompleteTaskRequest,
    PostTaskRequest,
    UbiClaimRequest,
)
from app.domains.economy.services import EconomyServices

router = APIRouter(tags=["economy"])

EconomyDep = Annotated[EconomyServices, Depends(get_economy)]


def _treasury_writes_allowed(request: Request | None = None) -> tuple[bool, str]:
    env = (os.getenv("ENV") or os.getenv("NODE_ENV") or "").strip().lower()
    # BUG-004 fix: ENV=local bypass removed — always require explicit token or flag
    allow_flag = (os.getenv("BRIDGE_ALLOW_TREASURY_WRITES") or "").strip().lower()
    if allow_flag in ("1", "true", "yes", "on"):
        return True, "allow_flag"
    token = (os.getenv("CFO_TOKEN") or "").strip()
    if token:
        hdr = ""
        if request is not None:
            hdr = (request.headers.get("X-CFO-Token") or request.headers.get("x-cfo-token") or "").strip()
        if hdr and hdr == token:
            return True, "token"
        return False, "token_required"
    return False, "disabled"


# ------------------------------------------------------------------
# Treasury
# ------------------------------------------------------------------

@router.post("/treasury/collect")
async def treasury_collect(
    payload: CollectRequest,
    request: Request,
    svc: EconomyDep,
) -> dict[str, Any]:
    allowed, reason = _treasury_writes_allowed(request)
    if not allowed:
        raise HTTPException(403, detail=f"Treasury writes disabled ({reason})")
    return await svc.collect(
        amount=payload.amount,
        currency=payload.currency,
        source_project=payload.source_project,
        method=payload.method,
        type=payload.type,
        meta=payload.meta,
    )


@router.get("/treasury/status")
async def treasury_status(svc: EconomyDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.treasury_status()


@router.get("/treasury/ledger")
async def treasury_ledger(
    svc: EconomyDep,
    _: dict = Depends(require_jwt),
    limit: int = 50,
) -> dict[str, Any]:
    ledger = await svc.treasury_ledger(limit=limit)
    return {"ok": True, "ledger": ledger, "count": len(ledger)}


@router.get("/treasury/audit")
async def treasury_audit(limit: int = 50, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    """Return recent Transaction nodes from Neo4j payment audit trail."""
    from app.services.neo4j_connection import get_neo4j_connection
    records = get_neo4j_connection().get_payment_audit(limit=limit)
    return {"ok": True, "audit": records, "count": len(records)}


@router.post("/treasury/disburse")
async def treasury_disburse(
    payload: dict[str, Any],
    request: Request,
    svc: EconomyDep,
) -> dict[str, Any]:
    allowed, reason = _treasury_writes_allowed(request)
    if not allowed:
        raise HTTPException(403, detail=f"Treasury writes disabled ({reason})")
    bucket = payload.get("bucket", "")
    amount = float(payload.get("amount", 0))
    destination = payload.get("destination", "")
    authorized_by = payload.get("authorized_by", "cfo")
    if not bucket or amount <= 0:
        raise HTTPException(422, detail="bucket and positive amount required")
    return await svc.treasury_disburse(
        bucket=bucket,
        amount=amount,
        destination=destination,
        authorized_by=authorized_by,
    )


# ------------------------------------------------------------------
# UBI
# ------------------------------------------------------------------

@router.get("/ubi/status")
async def ubi_status(
    address: str,
    svc: EconomyDep,
) -> dict[str, Any]:
    return await svc.ubi_status(address)


@router.post("/ubi/claim")
async def ubi_claim(
    payload: UbiClaimRequest,
    svc: EconomyDep,
) -> dict[str, Any]:
    return await svc.ubi_distribute(payload.address)


# ------------------------------------------------------------------
# Marketplace
# ------------------------------------------------------------------

@router.get("/marketplace/open")
async def marketplace_open(
    svc: EconomyDep,
    twin_id: str = "system",
) -> dict[str, Any]:
    tasks = svc.get_tasks(twin_id=twin_id, status="open")
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


@router.get("/marketplace/tasks")
async def marketplace_all(
    svc: EconomyDep,
    status: str = "open",
    twin_id: str = "system",
) -> dict[str, Any]:
    tasks = svc.get_tasks(twin_id=twin_id, status=status)
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


@router.post("/marketplace/post")
async def marketplace_post(
    payload: PostTaskRequest,
    svc: EconomyDep,
) -> dict[str, Any]:
    return svc.post_task(
        title=payload.title,
        value=payload.value,
        twin_id=payload.twin_id,
        tags=payload.tags,
        meta=payload.meta,
    )


@router.post("/marketplace/accept")
async def marketplace_accept(
    payload: AcceptTaskRequest,
    svc: EconomyDep,
) -> dict[str, Any]:
    return svc.accept_task(task_id=payload.task_id, twin_id=payload.twin_id)


@router.post("/marketplace/complete")
async def marketplace_complete(
    payload: CompleteTaskRequest,
    svc: EconomyDep,
) -> dict[str, Any]:
    return svc.complete_task(
        task_id=payload.task_id,
        twin_id=payload.twin_id,
        result=payload.result,
    )


@router.get("/marketplace/task/{task_id}")
async def marketplace_task(
    task_id: int,
    svc: EconomyDep,
) -> dict[str, Any]:
    task = svc.get_task(task_id)
    return {"ok": True, "task": task}


@router.post("/marketplace/task")
async def marketplace_add_task_raw(
    task: dict[str, Any],
    svc: EconomyDep,
) -> dict[str, Any]:
    """Legacy add-task path (no schema validation, accepts any dict)."""
    if not isinstance(task, dict):
        raise HTTPException(400, detail="invalid task")
    return svc.add_task_raw(task)


@router.post("/marketplace/pledge")
async def marketplace_pledge(
    data: dict[str, Any],
    svc: EconomyDep,
) -> dict[str, Any]:
    task_id = data.get("task_id")
    wallet = data.get("wallet")
    amount = data.get("amount")
    if not task_id or not wallet:
        raise HTTPException(400, detail="task_id and wallet required")
    try:
        amt = float(amount)  # type: ignore[arg-type]
    except Exception:
        raise HTTPException(400, detail="valid amount required") from None
    event_id = data.get("event_id")
    return svc.pledge_task(
        task_id=int(task_id),
        wallet=str(wallet),
        amount=amt,
        event_id=str(event_id) if event_id else None,
    )


# ------------------------------------------------------------------
# Revenue
# ------------------------------------------------------------------

@router.get("/revenue/summary")
async def revenue_summary(svc: EconomyDep) -> dict[str, Any]:
    return await svc.revenue_summary()


@router.get("/revenue/status")
async def revenue_status(svc: EconomyDep) -> dict[str, Any]:
    """Alias for /revenue/summary — legacy path compatibility."""
    return await svc.revenue_summary()


# ------------------------------------------------------------------
# Treasury controls + rails
# ------------------------------------------------------------------

@router.get("/treasury/controls")
async def treasury_controls(request: Request) -> dict[str, Any]:
    allowed, reason = _treasury_writes_allowed(request)
    token_configured = bool((os.getenv("CFO_TOKEN") or "").strip())
    return {
        "ok": True,
        "writes_allowed": bool(allowed),
        "mode": reason,
        "token_configured": token_configured,
        "observed_env": {
            "ENV": os.getenv("ENV"),
            "NODE_ENV": os.getenv("NODE_ENV"),
            "BRIDGE_ALLOW_TREASURY_WRITES": os.getenv("BRIDGE_ALLOW_TREASURY_WRITES"),
            "CFO_TOKEN_set": bool((os.getenv("CFO_TOKEN") or "").strip()),
        },
        "enablement": {
            "env_local": "Set ENV=local",
            "allow_flag": "Set BRIDGE_ALLOW_TREASURY_WRITES=1",
            "token": "Set CFO_TOKEN and send X-CFO-Token header",
        },
    }


@router.get("/treasury/rails")
async def list_rails(svc: EconomyDep) -> dict[str, Any]:
    return svc.list_rails()


# ------------------------------------------------------------------
# Payment webhooks
# ------------------------------------------------------------------

def _idem_header(request: Request) -> str | None:
    """RFC draft-ietf-httpapi-idempotency-key — client-supplied override."""
    v = request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key")
    v = (v or "").strip()
    return v or None


@router.post("/payments/webhook/paystack")
async def webhook_paystack(request: Request, svc: EconomyDep) -> dict[str, Any]:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    result = await svc.webhook_paystack(body, signature, idem_override=_idem_header(request))
    # Auto-reconcile matching invoice if a payment came in
    if result.get("ok") and result.get("type") == "payment":
        try:
            from app.domains.billing.deps import get_billing
            billing = get_billing()
            await billing.reconcile_by_amount(
                amount=result.get("amount", 0),
                currency=result.get("currency", "ZAR"),
                payment_method="paystack",
            )
        except Exception:
            pass  # non-critical — treasury already collected
    return result


@router.post("/payments/webhook/paypal")
async def webhook_paypal(request: Request, svc: EconomyDep) -> dict[str, Any]:
    body = await request.body()
    headers = dict(request.headers)
    return await svc.webhook_paypal(body, headers, idem_override=_idem_header(request))


@router.post("/payments/webhook/crypto")
async def webhook_crypto(request: Request, svc: EconomyDep) -> dict[str, Any]:
    body = await request.body()
    return await svc.webhook_crypto(body, idem_override=_idem_header(request))


@router.post("/payments/webhook/payfast")
async def webhook_payfast(request: Request, svc: EconomyDep) -> dict[str, Any]:
    form = await request.form()
    form_dict = {k: str(v) for k, v in form.items()}
    return await svc.webhook_payfast(form_dict, idem_override=_idem_header(request))


@router.post("/payments/webhook/{rail}")
async def webhook_generic(rail: str, request: Request, svc: EconomyDep) -> dict[str, Any]:
    body = await request.body()
    source_project = request.headers.get("X-Source-Project") or None
    return await svc.webhook_generic(rail, body, source_project=source_project, idem_override=_idem_header(request))


# ------------------------------------------------------------------
# Demand Pump — backfill marketplace with synthetic tasks to maintain
# a minimum open-task backlog for agent activity.
# ------------------------------------------------------------------

@router.post("/demand/pump")
async def demand_pump(
    payload: dict[str, Any],
    svc: EconomyDep,
) -> dict[str, Any]:
    """Ensure at least `target_backlog` open tasks exist; create up to `max_create`."""
    target_backlog = int(payload.get("target_backlog", 5))
    max_create = int(payload.get("max_create", 10))

    open_tasks = svc.get_tasks(status="open")
    open_count = len(open_tasks)
    deficit = max(0, target_backlog - open_count)
    to_create = min(deficit, max_create)

    created = []
    for i in range(to_create):
        result = svc.post_task(
            title=f"Auto-generated task #{open_count + i + 1}",
            value=10.0,
            twin_id="system",
            tags=["auto", "demand-pump"],
        )
        created.append(result.get("task_id"))

    return {
        "ok": True,
        "open_tasks": open_count,
        "target_backlog": target_backlog,
        "created": len(created),
        "task_ids": created,
    }
