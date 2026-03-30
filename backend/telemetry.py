from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from db import db

router = APIRouter()


@router.post("/api/telemetry/")
async def log_event(payload: dict):
    """Log a telemetry event"""
    event_id = str(uuid4())
    event_type = payload.get("event_type", "unknown")
    source = payload.get("source", "system")
    data = payload.get("data", {})

    try:
        await db.execute("""
            INSERT INTO telemetry (id, event_type, source, data, timestamp)
            VALUES ($1,$2,$3,$4,$5)
        """,
        event_id,
        event_type,
        source,
        str(data),
        datetime.utcnow()
        )

        return {
            "id": event_id,
            "status": "logged"
        }
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/telemetry/")
async def get_telemetry(event_type: str = None, source: str = None, limit: int = 100):
    """Get telemetry events"""
    try:
        query = "SELECT * FROM telemetry WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type=$" + str(len(params) + 1)
            params.append(event_type)

        if source:
            query += " AND source=$" + str(len(params) + 1)
            params.append(source)

        query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        events = await db.fetch(query, *params)
        return [dict(e) for e in events]
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/telemetry/events/count")
async def get_event_count(event_type: str = None):
    """Get count of events by type"""
    try:
        if event_type:
            count = await db.fetchval("""
                SELECT COUNT(*) FROM telemetry WHERE event_type=$1
            """, event_type)
        else:
            events = await db.fetch("""
                SELECT event_type, COUNT(*) as count
                FROM telemetry
                GROUP BY event_type
                ORDER BY count DESC
            """)
            return [dict(e) for e in events]

        return {"event_type": event_type, "count": count or 0}
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")
