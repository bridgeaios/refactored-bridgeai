"""
Network domain router.
Absorbs replication/*, swarm/*, network/*, projects/*, nodes/* from routes/api.py and routes/projects.py.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.domains.network.deps import get_network
from app.domains.infra.deps import require_jwt
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


# ------------------------------------------------------------------
# OSINT Agents — absorbed from backend/agents.py + tasks.py + ledger.py
# Entry point: uvicorn app.main:app (not backend/main.py which is dev-only)
# ------------------------------------------------------------------

@router.post("/agents")
async def create_agent(payload: dict[str, Any], svc: NetworkDep, _: dict = Depends(require_jwt)) -> dict[str, Any]:
    return await svc.create_agent(
        name=payload.get("name", ""),
        agent_type=payload.get("type", "leadgen"),
    )


@router.get("/agents")
async def list_agents(svc: NetworkDep) -> dict[str, Any]:
    agents = await svc.list_agents()
    return {"ok": True, "agents": agents, "count": len(agents)}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, svc: NetworkDep) -> dict[str, Any]:
    agent = await svc.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/agents/{agent_id}/tasks")
async def create_agent_task(
    agent_id: str, payload: dict[str, Any], svc: NetworkDep, _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    return await svc.create_task(agent_id=agent_id, task_payload=payload.get("payload", {}))


@router.get("/agents/{agent_id}/tasks")
async def list_agent_tasks(
    agent_id: str, svc: NetworkDep, status: str | None = None,
) -> dict[str, Any]:
    tasks = await svc.list_tasks(agent_id=agent_id, status=status)
    return {"ok": True, "tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, svc: NetworkDep) -> dict[str, Any]:
    task = await svc.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/osint/ledger")
async def osint_ledger(svc: NetworkDep, limit: int = 100) -> dict[str, Any]:
    entries = await svc.ledger_entries(limit=limit)
    return {"ok": True, "entries": entries, "count": len(entries)}


@router.post("/osint/register")
async def osint_register(payload: dict[str, Any], svc: NetworkDep) -> dict[str, Any]:
    """Register an OSINT-enriched lead profile. Called internally by workers.py."""
    from app.core.deps import get_memory
    mem = get_memory()
    from uuid import uuid4
    from datetime import datetime

    profile_id = str(uuid4())
    profile = {
        "id": profile_id,
        "task_id": payload.get("task_id"),
        "url": payload.get("url"),
        "title": payload.get("title"),
        "emails": payload.get("emails", []),
        "company_name": payload.get("company_name"),
        "industry": payload.get("industry"),
        "size_estimate": payload.get("size_estimate"),
        "template_type": payload.get("template_type"),
        "profile_confidence": payload.get("profile_confidence", 0),
        "full_profile": payload.get("full_profile", {}),
        "registered_at": datetime.utcnow().isoformat(),
    }
    await mem.set(f"osint:profile:{profile_id}", profile)
    # Append to index
    ids: list = await mem.get("osint:profiles:index") or []
    ids.append(profile_id)
    await mem.set("osint:profiles:index", ids)
    return {"ok": True, "id": profile_id}


@router.get("/osint/profiles")
async def list_osint_profiles(
    _: dict = Depends(require_jwt), limit: int = 50
) -> dict[str, Any]:
    """List registered OSINT profiles."""
    from app.core.deps import get_memory
    mem = get_memory()
    ids: list = await mem.get("osint:profiles:index") or []
    profiles = [await mem.get(f"osint:profile:{i}") for i in ids[-limit:]]
    profiles = [p for p in profiles if p]
    return {"ok": True, "profiles": profiles, "count": len(profiles)}
