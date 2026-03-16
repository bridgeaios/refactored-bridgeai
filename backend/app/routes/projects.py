"""
Projects Registry API — single source of truth for all projects in the Bridge AI OS ecosystem.

Endpoints:
  POST /api/projects/register       — any project registers itself at startup
  GET  /api/projects                — list all registered projects
  GET  /api/projects/{id}           — get a specific project
  POST /api/projects/{id}/heartbeat — keep-alive / status update
  DELETE /api/projects/{id}         — deregister a project
"""
from fastapi import APIRouter, HTTPException

from app.runtime import projects_service

router = APIRouter()


@router.post("/projects/register")
async def register_project(data: dict):
    """
    Register or update a project in the central registry.
    Any project (AOE, Supaco, Taurus, Next.js, etc.) calls this at startup.

    Required: { "id": "my-project" }
    Optional: label, type, baseUrl, apiUrl, health, port, capabilities, meta, status
    """
    try:
        entry = await projects_service.register(data)
        return {"ok": True, "project": entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/projects")
async def list_projects():
    """
    Return all registered projects — the single source of truth for the full ecosystem.
    Any project or UI can call this to discover the live platform map.
    """
    projects = await projects_service.list_projects()
    return {
        "ok": True,
        "count": len(projects),
        "projects": projects,
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific registered project by id."""
    project = await projects_service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not registered")
    return {"ok": True, "project": project}


@router.post("/projects/{project_id}/heartbeat")
async def project_heartbeat(project_id: str, data: dict | None = None):
    """
    Keep-alive endpoint. Projects call this periodically to report they are online.
    Optional body: { "status": "online" | "degraded" | "offline" }
    """
    status = (data or {}).get("status", "online")
    updated = await projects_service.heartbeat(project_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not registered — call /api/projects/register first")
    return {"ok": True, "project": updated}


@router.delete("/projects/{project_id}")
async def deregister_project(project_id: str):
    """Remove a project from the registry."""
    removed = await projects_service.deregister(project_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"project '{project_id}' not found")
    return {"ok": True, "removed": project_id}
