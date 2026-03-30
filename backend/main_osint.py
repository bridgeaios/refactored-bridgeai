import asyncio
import hashlib
import os
from datetime import datetime

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import execution layer
from db import db
from workers import worker_loop
from agents import router as agents_router
from tasks import router as tasks_router
from ledger import router as ledger_router
from treasury import router as treasury_router
from telemetry import router as telemetry_router

app = FastAPI()

# CORS middleware
_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(ledger_router)
app.include_router(treasury_router)
app.include_router(telemetry_router)

ROOT = os.environ.get("BRIDGE_OUTPUT_ROOT", "./output")

STATE = {
    "status": "idle",
    "last_run": None,
    "merkle": None,
    "agents": {},
    "history": [],
    "worker_task": None
}

# ===== STARTUP / SHUTDOWN =====
@app.on_event("startup")
async def startup():
    """Initialize database and start worker loop"""
    print(f"[STARTUP] FastAPI server starting... (timestamp: {datetime.utcnow().isoformat()})")
    try:
        await db.connect()
        print("[STARTUP] [OK] Database connected")

        # Start worker loop in background
        STATE["worker_task"] = asyncio.create_task(worker_loop())
        print("[STARTUP] [OK] Worker loop started in background")
    except Exception as e:
        print(f"[STARTUP] [FAIL] Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    try:
        if STATE["worker_task"]:
            STATE["worker_task"].cancel()
        await db.disconnect()
        print("[INFO] Database disconnected")
    except Exception as e:
        print(f"[ERROR] Shutdown error: {e}")

app.mount("/output", StaticFiles(directory=ROOT), name="output")

# -------------------------
# TRUE MERKLE (filesystem)
# -------------------------
def hash_file(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def build_merkle():
    hashes = []
    for root,_,files in os.walk(ROOT):
        for f in files:
            p = os.path.join(root,f)
            hashes.append(hash_file(p))
    hashes.sort()
    if not hashes:
        return None
    while len(hashes) > 1:
        hashes = [
            hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
            for i in range(0,len(hashes)-1,2)
        ]
    return hashes[0]

# -------------------------
# DELTA BUILD DETECTION
# -------------------------
LAST_HASH = None

def delta_check():
    global LAST_HASH
    new_hash = build_merkle()
    changed = new_hash != LAST_HASH
    LAST_HASH = new_hash
    return changed, new_hash

# -------------------------
# TELEMETRY
# -------------------------
@app.post("/telemetry/events")
async def telemetry(data: dict):
    ts = datetime.utcnow().isoformat()
    changed, merkle = delta_check()

    STATE["status"] = data.get("status")
    STATE["last_run"] = ts
    STATE["merkle"] = merkle

    entry = {
        "timestamp": ts,
        "status": data.get("status"),
        "merkle": merkle
    }

    STATE["history"].append(entry)

    # register agent
    agent = data.get("agent","node-1")
    STATE["agents"][agent] = {
        "last_seen": ts,
        "status": data.get("status")
    }

    return {"ok":True,"delta":changed,"merkle":merkle}

# -------------------------
# WEBSOCKET STREAM
# -------------------------
clients = []

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            await asyncio.sleep(1)
            await ws.send_json(STATE)
    except Exception:
        clients.remove(ws)

# -------------------------
# HEALTH
# -------------------------
@app.get("/health")
def health():
    return {"status":"ok"}
