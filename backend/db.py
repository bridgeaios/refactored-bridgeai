import aiosqlite
import os
import json
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bridgeai.db")

class Database:
    def __init__(self):
        self.db = None

    async def connect(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self._init_tables()

    async def _init_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'leadgen',
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                agent_id TEXT,
                amount REAL,
                transaction_type TEXT DEFAULT 'internal',
                description TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                event TEXT,
                data TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                url TEXT,
                title TEXT,
                emails TEXT,
                osint_profile TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await self.db.commit()

    async def disconnect(self):
        if self.db:
            await self.db.close()

    async def execute(self, query: str, *args):
        # Convert $1, $2 style params to ? style for SQLite
        q = self._convert_params(query)
        cursor = await self.db.execute(q, args)
        await self.db.commit()
        return cursor

    async def fetch(self, query: str, *args):
        q = self._convert_params(query)
        cursor = await self.db.execute(q, args)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetchval(self, query: str, *args) -> Optional:
        q = self._convert_params(query)
        cursor = await self.db.execute(q, args)
        row = await cursor.fetchone()
        return row[0] if row else None

    async def fetchrow(self, query: str, *args):
        q = self._convert_params(query)
        cursor = await self.db.execute(q, args)
        row = await cursor.fetchone()
        return dict(row) if row else None

    def _convert_params(self, query: str) -> str:
        """Convert PostgreSQL $1, $2 params to SQLite ? params"""
        import re
        return re.sub(r'\$\d+', '?', query)

db = Database()
