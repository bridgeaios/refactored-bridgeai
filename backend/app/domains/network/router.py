"""
Network domain router.
Absorbs replication/*, swarm/*, network/*, projects/*, nodes/* from routes/api.py and routes/projects.py.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.network.deps import get_network
from app.domains.network.models import ProjectRegisterRequest, SwarmMessageRequest
from app.domains.network.services import NetworkServices

router = APIRouter(tags=["network"])

NetworkDep = Annotated[NetworkServices, Depends(get_network)]


@router.get("/network/status")
async def network_status(svc: NetworkDep) -> dict[str, Any]:
    return await svc.network_status()


@router.get("/swarm/health")
async def swarm_health(svc: NetworkDep) -> dict[str, Any]:
    return await svc.swarm_health()


@router.post("/swarm/broadcast")
async def swarm_broadcast(
    payload: SwarmMessageRequest,
    svc: NetworkDep,
) -> dict[str, Any]:
    return await svc.swarm_broadcast(
        channel=payload.channel,
        payload=payload.payload,
        sender_id=payload.sender_id,
    )


@router.get("/projects")
async def list_projects(svc: NetworkDep) -> dict[str, Any]:
    projects = await svc.list_projects()
    return {"ok": True, "projects": projects, "count": len(projects)}


@router.post("/projects/register")
async def register_project(
    payload: ProjectRegisterRequest,
    svc: NetworkDep,
) -> dict[str, Any]:
    return await svc.register_project(name=payload.name, url=payload.url, meta=payload.meta)


@router.get("/projects/{project_id}")
async def get_project(project_id: str, svc: NetworkDep) -> dict[str, Any]:

    project = await svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not registered")
    return {"ok": True, "project": project}


@router.post("/projects/{project_id}/heartbeat")
async def project_heartbeat(
    project_id: str,
    svc: NetworkDep,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:

    status = (data or {}).get("status", "online")
    updated = await svc.project_heartbeat(project_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not registered")
    return {"ok": True, "project": updated}


@router.delete("/projects/{project_id}")
async def deregister_project(project_id: str, svc: NetworkDep) -> dict[str, Any]:

    removed = await svc.deregister_project(project_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not found")
    return {"ok": True, "removed": project_id}


# ------------------------------------------------------------------
# Replication engine (from routes/api.py)
# ------------------------------------------------------------------

@router.get("/replication/status")
async def replication_status(svc: NetworkDep) -> dict[str, Any]:
    return await svc.replication_status()


@router.get("/replication/nodes")
async def replication_nodes(svc: NetworkDep) -> dict[str, Any]:
    nodes = await svc.replication_nodes()
    return {"ok": True, "nodes": nodes}


@router.post("/replication/register")
async def replication_register(data: dict[str, Any], svc: NetworkDep) -> dict[str, Any]:
    node_id = data.get("node_id")
    url = data.get("url")
    if not node_id or not url:
        raise HTTPException(status_code=400, detail="node_id and url required")
    capabilities = data.get("capabilities")
    if isinstance(capabilities, str):
        capabilities = [c.strip() for c in capabilities.split(",") if c.strip()]
    return await svc.replication_register(node_id=str(node_id), url=str(url), capabilities=capabilities)
