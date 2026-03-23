"""
Economy domain router.

Replaces economy-related endpoints previously scattered across:
  - routes/api.py  (marketplace, ubi, revenue endpoints)
  - routes/treasury.py  (treasury endpoints)

All endpoints preserved at identical paths. No breaking changes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domains.economy.deps import get_economy
from app.domains.economy.models import (
    AcceptTaskRequest,
    CollectRequest,
    CompleteTaskRequest,
    PostTaskRequest,
    UbiClaimRequest,
)
from app.domains.economy.services import EconomyServices

router = APIRouter(tags=["economy"])


# ------------------------------------------------------------------
# Treasury
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# UBI
# ------------------------------------------------------------------

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
    return await svc.ubi_distribute(payload.address)


# ------------------------------------------------------------------
# Marketplace
# ------------------------------------------------------------------

@router.get("/marketplace/open")
async def marketplace_open(
    twin_id: str = "system",
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    tasks = svc.get_tasks(twin_id=twin_id, status="open")
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


@router.get("/marketplace/tasks")
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
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    return svc.accept_task(task_id=payload.task_id, twin_id=payload.twin_id)


@router.post("/marketplace/complete")
async def marketplace_complete(
    payload: CompleteTaskRequest,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    return svc.complete_task(
        task_id=payload.task_id,
        twin_id=payload.twin_id,
        result=payload.result,
    )


@router.get("/marketplace/task/{task_id}")
async def marketplace_task(
    task_id: int,
    svc: EconomyServices = Depends(get_economy),
) -> dict[str, Any]:
    task = svc.get_task(task_id)
    return {"ok": True, "task": task}


# ------------------------------------------------------------------
# Revenue
# ------------------------------------------------------------------

@router.get("/revenue/summary")
async def revenue_summary(svc: EconomyServices = Depends(get_economy)) -> dict[str, Any]:
    return await svc.revenue_summary()
