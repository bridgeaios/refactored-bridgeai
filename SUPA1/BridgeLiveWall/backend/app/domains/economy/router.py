#
# ruff: noqa: B008
"""
Economy domain: treasury, UBI, marketplace, revenue, bossbots trading.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.domains.economy.deps import get_economy
from app.domains.economy.models import CollectRequest, PostTaskRequest, UbiClaimRequest
from app.domains.economy.services import EconomyServices
from app.physics import (
    check_economic_risk,
    record_economic_action,
    replenish_evolution_budget,
    telemetry,
)
from app.runtime import bossbots_service, revenue_service, sdg_service, ubi_service

router = APIRouter(tags=["economy"])


# --- Treasury (plan + new) ---


@router.post("/treasury/collect")
async def treasury_collect(
    payload: CollectRequest,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    return await svc.collect(
        amount=payload.amount,
        currency=payload.currency,
        source_project=payload.source_project,
        method=payload.method,
        type=payload.type,
        meta=payload.meta,
    )


@router.get("/treasury/status")
async def treasury_status(svc: EconomyServices = Depends(get_economy)) -> dict[str, Any]:
    return await svc.treasury_status()


@router.get("/treasury/ledger")
async def treasury_ledger(
    limit: int = 50,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    ledger = await svc.treasury_ledger(limit=limit)
    return {"ok": True, "ledger": ledger, "count": len(ledger)}


@router.post("/treasury/disburse")
async def treasury_disburse(
    payload: dict[str, Any],
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
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


# --- UBI ---


@router.get("/ubi/status")
async def ubi_status(
    address: str,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    return await svc.ubi_status(address)


@router.post("/ubi/claim")
async def ubi_claim(
    payload: UbiClaimRequest,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    """UBI claim — same behaviour as legacy /api/ubi/claim."""
    _ = svc
    address = payload.address
    twin_id = str(address)[:16]
    amount = ubi_service.amount
    allowed, reason = check_economic_risk(twin_id, amount)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    distributed = ubi_service.distribute(address)
    if distributed > 0:
        record_economic_action(twin_id, float(distributed))
        sdg_service.track("ubi_claims", 1)
        telemetry.record_economic_conversion()
        replenish_evolution_budget(min(0.5, float(distributed) / 200), "economic_surplus")
    return {"ok": True, "amount": distributed}


# --- Marketplace (plan aliases + legacy paths) ---


@router.get("/marketplace/open")
async def marketplace_open(
    twin_id: str = "system",
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    tasks = svc.get_tasks(twin_id=twin_id, status="open")
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


@router.get("/marketplace/tasks")
async def marketplace_tasks(status: Optional[str] = None) -> list[dict]:
    """Legacy: returns a raw list of tasks."""
    from app.domains.economy.deps import get_economy

    return get_economy()._marketplace.get_tasks(status=status)


@router.get("/marketplace/all")
async def marketplace_all(
    status: str = "open",
    twin_id: str = "system",
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    tasks = svc.get_tasks(twin_id=twin_id, status=status)
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


@router.post("/marketplace/post")
async def marketplace_post(
    payload: PostTaskRequest,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    result = svc.post_task(
        title=payload.title,
        value=payload.value,
        twin_id=payload.twin_id,
        tags=payload.tags,
        meta=payload.meta,
    )
    sdg_service.track("tasks_created", 1)
    try:
        fee = float(payload.value) * 0.05
        revenue_service.collect(fee)
    except Exception:
        pass
    return result


@router.post("/marketplace/task")
async def marketplace_task_legacy(task: dict) -> dict[str, Any]:
    """Legacy create task — body shape unchanged."""
    if not isinstance(task, dict):
        raise HTTPException(status_code=400, detail="invalid task")
    from app.domains.economy.deps import get_economy

    svc = get_economy()
    t = svc._marketplace.add_task(task)
    sdg_service.track("tasks_created", 1)
    try:
        reward = float(task.get("reward", 0))
        fee = reward * 0.05
        revenue_service.collect(fee)
    except Exception:
        pass
    return {"status": "created", "task": t}


@router.post("/marketplace/pledge")
async def marketplace_pledge(data: dict) -> dict[str, Any]:
    from app.domains.economy.deps import get_economy

    svc = get_economy()
    task_id = data.get("task_id")
    wallet = data.get("wallet")
    amount = data.get("amount")
    event_id = data.get("event_id")
    if not task_id or not wallet:
        raise HTTPException(status_code=400, detail="task_id and wallet required")
    try:
        amt = float(amount)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="valid amount required") from exc
    if amt <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    pledge_task_id = int(task_id)
    pledge_wallet = str(wallet)
    pledge_event_id = str(event_id) if event_id else None
    t = svc._marketplace.pledge_task(pledge_task_id, pledge_wallet, amt, pledge_event_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    try:
        revenue_service.collect(max(0.01, amt * 0.01))
    except Exception:
        pass
    return {"status": "pledged", "task": t, "event_id": event_id}


@router.post("/marketplace/accept")
async def marketplace_accept(data: dict[str, Any]) -> dict[str, Any]:
    """
    Accept a task. Legacy body: {task_id, wallet}. Plan body: {task_id, twin_id}.
    """
    from app.domains.economy.deps import get_economy

    svc = get_economy()
    task_id = data.get("task_id")
    wallet = data.get("wallet")
    twin_id = data.get("twin_id")
    if wallet is not None and task_id is not None:
        t = svc._marketplace.accept_task(int(task_id), str(wallet))
        if not t:
            raise HTTPException(status_code=404, detail="task not available")
        return {"status": "accepted", "task": t}
    if twin_id is not None and task_id is not None:
        return svc.accept_task(task_id=int(task_id), twin_id=str(twin_id))
    raise HTTPException(status_code=400, detail="task_id and wallet or twin_id required")


@router.post("/marketplace/complete")
async def marketplace_complete(data: dict[str, Any]) -> dict[str, Any]:
    """Legacy: {task_id}. Plan: may include twin_id, result (ignored for competition flow)."""
    from app.domains.economy.deps import get_economy

    svc = get_economy()
    task_id = data.get("task_id")
    if task_id is None:
        raise HTTPException(status_code=400, detail="task_id required")
    t = svc._competition.complete_task(int(task_id), svc._marketplace)
    if not t:
        raise HTTPException(status_code=404, detail="task not found or not in progress")
    sdg_service.track("tasks_completed", 1)
    return {"status": "completed", "task": t}


@router.get("/marketplace/task/{task_id}")
async def marketplace_task_get(
    task_id: int,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    task = svc.get_task(task_id)
    return {"ok": True, "task": task}


# --- Revenue ---


@router.get("/revenue/summary")
async def revenue_summary(svc: EconomyServices = Depends(get_economy)) -> dict[str, Any]:
    return await svc.revenue_summary()


@router.get("/revenue/status")
async def revenue_status() -> dict[str, Any]:
    return revenue_service.get_status()


# --- BossBots ---


@router.post("/bossbots/trade")
async def bossbots_trade(trade: dict) -> dict[str, Any]:
    from app.runtime import twins_competition

    asset = trade.get("asset") if isinstance(trade, dict) else None
    if not asset:
        raise HTTPException(status_code=400, detail="asset required")
    twin_id = trade.get("twin_id", "system")
    amount = 0.05
    allowed, reason = check_economic_risk(twin_id, amount)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    signal = bossbots_service.generate_signal(asset)
    twin_executions = twins_competition.execute_signal_for_twins(asset, signal)
    collected = revenue_service.collect(0.05)
    if collected:
        record_economic_action(twin_id, amount)
        sdg_service.track("trades_executed", 1)
        telemetry.record_economic_conversion()
        replenish_evolution_budget(0.1, "economic_surplus")
    return {"signal": signal, "twins_followed": twin_executions}


@router.get("/bossbots/signals")
async def bossbots_signals() -> dict[str, Any]:
    return bossbots_service.get_signals()
