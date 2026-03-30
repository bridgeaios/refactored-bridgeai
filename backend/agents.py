from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from db import db

router = APIRouter()


@router.post("/api/agents/")
async def create_agent(payload: dict):
    """Create a new agent"""
    agent_id = str(uuid4())
    name = payload.get("name", "agent-" + agent_id[:8])
    agent_type = payload.get("type", "standard")

    try:
        await db.execute("""
            INSERT INTO agents (id, name, type, status, created_at)
            VALUES ($1,$2,$3,$4,$5)
        """, agent_id, name, agent_type, "active", datetime.utcnow())

        return {
            "id": agent_id,
            "name": name,
            "type": agent_type,
            "status": "active"
        }
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    try:
        agent = await db.fetchrow("""
            SELECT * FROM agents WHERE id=$1
        """, agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return dict(agent)
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/agents/")
async def list_agents():
    """List all agents"""
    try:
        agents = await db.fetch("""
            SELECT * FROM agents ORDER BY created_at DESC
        """)

        return [dict(a) for a in agents]
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")
