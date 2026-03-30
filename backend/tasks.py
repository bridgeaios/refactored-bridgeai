from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from db import db

router = APIRouter()


@router.post("/api/tasks/")
async def create_task(payload: dict):
    """Create a new task"""
    task_id = str(uuid4())
    agent_id = payload.get("agent_id")
    task_payload = payload.get("payload", {})

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")

    try:
        # Verify agent exists
        agent = await db.fetchrow("SELECT id FROM agents WHERE id=$1", agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Create task
        await db.execute("""
            INSERT INTO tasks (id, agent_id, payload, status, created_at)
            VALUES ($1,$2,$3,$4,$5)
        """, task_id, agent_id, str(task_payload), "pending", datetime.utcnow())

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    try:
        task = await db.fetchrow("""
            SELECT * FROM tasks WHERE id=$1
        """, task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return dict(task)
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/tasks/")
async def list_tasks(agent_id: str = None, status: str = None):
    """List tasks with optional filters"""
    try:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if agent_id:
            query += " AND agent_id=$" + str(len(params) + 1)
            params.append(agent_id)

        if status:
            query += " AND status=$" + str(len(params) + 1)
            params.append(status)

        query += " ORDER BY created_at DESC"

        tasks = await db.fetch(query, *params)
        return [dict(t) for t in tasks]
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")
