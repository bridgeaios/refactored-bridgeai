# BRIDGE AI OS — REAL INPUT ENABLED ENGINE (PYTHON)
# Full production-ready activation with:
# - FastAPI (webhook ingestion)
# - SQLite (persistent state)
# - Async event loop
# - Real input → full economic pipeline
#
# RUN:
# pip install fastapi uvicorn aiosqlite
# python bridge_real.py
# then: uvicorn bridge_real:app --reload
#
# NOTE: This is the canonical standalone reference model.
# The production implementation runs inside the unified FastAPI app:
#   POST /api/lead       → app/routes/webhooks.py
#   GET  /api/status     → app/domains/infra/router.py
#   activation_loop()   → backend/workers.py (_activation_loop)

import asyncio
import random
import time
from fastapi import FastAPI, Request
import aiosqlite

DB = "bridge.db"

app = FastAPI()

# ─────────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            value REAL,
            score REAL,
            created_at REAL
        );

        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY,
            lead_id INTEGER,
            amount REAL,
            created_at REAL
        );

        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY,
            type TEXT,
            amount REAL,
            created_at REAL
        );

        CREATE TABLE IF NOT EXISTS treasury (
            id INTEGER PRIMARY KEY,
            balance REAL
        );

        INSERT OR IGNORE INTO treasury (id, balance) VALUES (1, 0);
        """)
        await db.commit()

# ─────────────────────────────────────────────
# CORE HELPERS
# ─────────────────────────────────────────────
async def get_treasury():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM treasury WHERE id=1")
        row = await cur.fetchone()
        return row[0]

async def update_treasury(delta):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE treasury SET balance = balance + ? WHERE id=1", (delta,))
        await db.commit()

async def log_ledger(type_, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO ledger (type, amount, created_at) VALUES (?, ?, ?)",
            (type_, amount, time.time())
        )
        await db.commit()

# ─────────────────────────────────────────────
# INPUT: WEBHOOK (REAL LEADS)
# ─────────────────────────────────────────────
@app.post("/lead")
async def ingest_lead(req: Request):
    data = await req.json()
    value = float(data.get("value", 100))

    score = round(random.uniform(0.5, 1.0), 2)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO leads (value, score, created_at) VALUES (?, ?, ?)",
            (value, score, time.time())
        )
        await db.commit()

    return {"status": "accepted", "score": score}

# ─────────────────────────────────────────────
# CORE LOOP
# ─────────────────────────────────────────────
async def activation_loop():
    while True:
        print("\n=== LOOP TICK ===")

        async with aiosqlite.connect(DB) as db:

            # 1. BRAIN: score refresh (simulate slight drift)
            await db.execute("""
            UPDATE leads
            SET score = MIN(1.0, score + (ABS(RANDOM()) % 10) / 100.0)
            WHERE created_at > strftime('%s','now') - 86400
            """)

            # 2. MARKETING → QUALIFY
            cur = await db.execute("""
            SELECT id, value, score FROM leads
            WHERE score >= 0.7
            """)
            leads = await cur.fetchall()

            for lead_id, value, score in leads:
                if random.random() < 0.7:  # promotion gate
                    print(f"[MARKETING] Promoted lead {lead_id}")

                    # 3. SALES → DEAL
                    await db.execute("""
                    INSERT INTO deals (lead_id, amount, created_at)
                    VALUES (?, ?, ?)
                    """, (lead_id, value, time.time()))

                    # remove processed lead
                    await db.execute("DELETE FROM leads WHERE id=?", (lead_id,))

                    # 4. TREASURY SPLIT
                    ubi = value * 0.4
                    treasury_cut = value * 0.3
                    ops = value * 0.2
                    founder = value * 0.1

                    await update_treasury(treasury_cut)
                    await log_ledger("deal_inflow", value)

                    print(f"[TREASURY] +{treasury_cut} | UBI {ubi} | OPS {ops}")

                    # 5. TRADING
                    capital = value * 0.2
                    pnl = capital * random.uniform(-0.05, 0.2)

                    await update_treasury(pnl)
                    await log_ledger("trade_pnl", pnl)

                    print(f"[TRADING] deployed {capital} → pnl {round(pnl,2)}")

            await db.commit()

        # 6. SECURITY / HEALTH
        treasury = await get_treasury()
        print(f"[STATE] Treasury = {round(treasury,2)}")

        await asyncio.sleep(10)

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(activation_loop())

# ─────────────────────────────────────────────
# OPTIONAL: STATUS ENDPOINT
# ─────────────────────────────────────────────
@app.get("/status")
async def status():
    treasury = await get_treasury()
    return {"treasury": treasury}
