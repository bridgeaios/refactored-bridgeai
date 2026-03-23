"""
Network domain router.
Absorbs replication/*, swarm/*, network/*, projects/*, nodes/* from routes/api.py and routes/projects.py.
"""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from app.domains.network.deps import get_network
from app.domains.network.models import ProjectRegisterRequest, SwarmMessageRequest
from app.domains.network.services import NetworkServices

router = APIRouter(tags=["network"])


@router.get("/network/status")
async def network_status(svc: NetworkServices = Depends(get_network)) -> dict[str, Any]:
    return await svc.network_status()


@router.get("/swarm/health")
async def swarm_health(svc: NetworkServices = Depends(get_network)) -> dict[str, Any]:
    return await svc.swarm_health()


@router.post("/swarm/broadcast")
async def swarm_broadcast(
    payload: SwarmMessageRequest,
    svc: NetworkServices = Depends(get_network),
) -> dict[str, Any]:
    return await svc.swarm_broadcast(
        channel=payload.channel,
        payload=payload.payload,
        sender_id=payload.sender_id,
    )


@router.get("/projects")
async def list_projects(svc: NetworkServices = Depends(get_network)) -> dict[str, Any]:
    projects = await svc.list_projects()
    return {"ok": True, "projects": projects, "count": len(projects)}


@router.post("/projects/register")
async def register_project(
    payload: ProjectRegisterRequest,
    svc: NetworkServices = Depends(get_network),
) -> dict[str, Any]:
    return await svc.register_project(name=payload.name, url=payload.url, meta=payload.meta)
