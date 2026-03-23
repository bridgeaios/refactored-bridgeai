from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import hashlib, os, json, asyncio

app = FastAPI()

ROOT = "E:/A/output"

STATE = {
    "status": "idle",
    "last_run": None,
    "merkle": None,
    "agents": {},
    "history": []
}

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
    if not hashes: return None
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
@app.post("/api/telemetry/events")
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
    except:
        clients.remove(ws)

# -------------------------
# HEALTH
# -------------------------
@app.get("/api/health")
def health():
    return {"status":"ok"}
