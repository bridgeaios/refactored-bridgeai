import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import hashlib
import json


class DistributionRequest(BaseModel):
    org_id: str
    user_id: str
    amount: float
    idempotency_key: str


def init_db():
    conn = sqlite3.connect("/data/bridge.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            idempotency_key TEXT UNIQUE NOT NULL,
            org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            fee REAL NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS treasury (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_distributed REAL DEFAULT 0,
            total_fees REAL DEFAULT 0,
            execution_count INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)

    c.execute("SELECT COUNT(*) FROM treasury")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO treasury (total_distributed, total_fees, execution_count, updated_at) VALUES (0, 0, 0, ?)",
            (datetime.utcnow().isoformat(),),
        )

    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://supaco.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_edge_access(x_edge_authorized: Optional[str] = Header(None)):
    if os.getenv("EDGE_MODE") == "required" and x_edge_authorized != "true":
        raise HTTPException(
            status_code=401, detail="Unauthorized: Must pass through edge"
        )


def get_db():
    conn = sqlite3.connect("/data/bridge.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bridge-backend",
        "edge_mode": os.getenv("EDGE_MODE", "disabled"),
        "version": "1.0.0",
    }


@app.post("/run-task")
async def run_task(
    data: dict,
    request: Request,
    x_edge_authorized: Optional[str] = Header(None),
):
    verify_edge_access(x_edge_authorized)
    return {
        "status": "success",
        "data": data,
    }


@app.post("/api/distribution/run")
async def run_distribution(
    req: DistributionRequest,
    request: Request,
    x_edge_authorized: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_org: Optional[str] = Header(None, alias="X-User-Org"),
):
    verify_edge_access(x_edge_authorized)

    if not x_user_id:
        raise HTTPException(status_code=401, detail="User identity required")

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT execution_id FROM executions WHERE idempotency_key = ?",
        (req.idempotency_key,),
    )
    existing = c.fetchone()

    if existing:
        conn.close()
        return {
            "success": False,
            "error": "Duplicate idempotency_key",
            "execution_id": existing[0],
        }

    fee = req.amount * 0.01
    net_amount = req.amount - fee
    execution_id = str(uuid.uuid4())
    input_hash = hashlib.sha256(
        json.dumps(req.dict(), sort_keys=True).encode()
    ).hexdigest()
    output_hash = hashlib.sha256(f"{execution_id}{net_amount}".encode()).hexdigest()

    now = datetime.utcnow().isoformat()
    c.execute(
        """
        INSERT INTO executions 
        (execution_id, idempotency_key, org_id, user_id, amount, fee, input_hash, output_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            execution_id,
            req.idempotency_key,
            req.org_id,
            req.user_id,
            req.amount,
            fee,
            input_hash,
            output_hash,
            "completed",
            now,
        ),
    )

    c.execute(
        "UPDATE treasury SET total_distributed = total_distributed + ?, total_fees = total_fees + ?, execution_count = execution_count + 1, updated_at = ?",
        (net_amount, fee, now),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "execution_id": execution_id,
        "data": {
            "gross_amount": req.amount,
            "fee": fee,
            "net_amount": net_amount,
            "input_hash": input_hash,
            "output_hash": output_hash,
        },
        "error": None,
    }


@app.get("/api/execution/{execution_id}")
async def get_execution(
    execution_id: str,
    x_edge_authorized: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    verify_edge_access(x_edge_authorized)

    if not x_user_id:
        raise HTTPException(status_code=401, detail="User identity required")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {"success": True, "data": dict(row), "error": None}


@app.get("/internal/treasury/summary")
async def treasury_summary(
    x_edge_authorized: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    verify_edge_access(x_edge_authorized)

    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM treasury LIMIT 1")
    row = c.fetchone()
    conn.close()

    return {
        "success": True,
        "data": {
            "total_distributed": row[1] if row else 0,
            "total_fees": row[2] if row else 0,
            "execution_count": row[3] if row else 0,
            "updated_at": row[4] if row else None,
        },
        "error": None,
    }


@app.get("/api/me")
async def get_current_user(
    x_edge_authorized: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_org: Optional[str] = Header(None, alias="X-User-Org"),
):
    verify_edge_access(x_edge_authorized)

    if not x_user_id:
        raise HTTPException(status_code=401, detail="User identity required")

    return {
        "success": True,
        "data": {"user_id": x_user_id, "org_id": x_user_org, "role": x_user_role},
        "error": None,
    }
