"""
lifecycle.py — Gap 19: Agent Lifecycle Management.

Tracks every agent instance from spawn → active → idle → retired.
Stores registry in MemoryStore. Workers call heartbeat() each cycle.
Control plane reads the registry for topology visualization.

Agent states:
  spawning  — registered but not yet confirmed active
  active    — sent heartbeat within HEARTBEAT_TTL
  idle      — no heartbeat for > HEARTBEAT_TTL but < RETIRE_TTL
  retired   — no heartbeat for > RETIRE_TTL (auto-retired)
  error     — last heartbeat reported an error

Usage:
    from app.core.lifecycle import register_agent, heartbeat, retire_agent, agent_registry

    agent_id = await register_agent(mem, name="osint_crawler", channel="X")
    await heartbeat(mem, agent_id, meta={"leads_scanned": 42})
    await retire_agent(mem, agent_id)
    agents = await agent_registry(mem)
"""
from __future__ import annotations

import json
import time
from uuid import uuid4

_PREFIX  = "agent:"
_INDEX   = "agents:index"

HEARTBEAT_TTL = 30    # seconds — idle after this
RETIRE_TTL    = 300   # seconds — auto-retired after this


# ── Registration ─────────────────────────────────────────────────────────────

async def register_agent(mem, name: str, channel: str, meta: dict | None = None) -> str:
    """Register a new agent instance. Returns the agent_id."""
    agent_id = f"{name}:{uuid4().hex[:8]}"
    record = {
        "id":         agent_id,
        "name":       name,
        "channel":    channel,
        "status":     "spawning",
        "spawned_at": time.time(),
        "last_hb":    None,
        "meta":       meta or {},
    }
    await mem.set(_PREFIX + agent_id, json.dumps(record))

    # Add to index
    raw = await mem.get(_INDEX)
    index: list[str] = json.loads(raw) if raw else []
    if agent_id not in index:
        index.append(agent_id)
    await mem.set(_INDEX, json.dumps(index))

    # Increment active count
    raw_count = await mem.get("agents:active:count")
    count = int(raw_count) if raw_count else 0
    await mem.set("agents:active:count", str(count + 1))

    return agent_id


async def heartbeat(mem, agent_id: str, meta: dict | None = None) -> bool:
    """Update an agent's heartbeat. Returns False if agent not found."""
    raw = await mem.get(_PREFIX + agent_id)
    if not raw:
        return False
    record = json.loads(raw)
    record["last_hb"] = time.time()
    record["status"]  = "active"
    if meta:
        record["meta"].update(meta)
    await mem.set(_PREFIX + agent_id, json.dumps(record))
    return True


async def retire_agent(mem, agent_id: str, reason: str = "manual") -> bool:
    """Mark an agent as retired."""
    raw = await mem.get(_PREFIX + agent_id)
    if not raw:
        return False
    record = json.loads(raw)
    prev_status = record.get("status")
    record["status"]      = "retired"
    record["retired_at"]  = time.time()
    record["retire_reason"] = reason
    await mem.set(_PREFIX + agent_id, json.dumps(record))

    # Decrement active count if was active/idle
    if prev_status in ("active", "idle", "spawning"):
        raw_count = await mem.get("agents:active:count")
        count = max(0, int(raw_count) - 1) if raw_count else 0
        await mem.set("agents:active:count", str(count))

    return True


async def agent_registry(mem, include_retired: bool = False) -> list[dict]:
    """
    Return all agents, auto-retiring stale ones.
    Agents with no heartbeat for > RETIRE_TTL are auto-retired.
    """
    raw = await mem.get(_INDEX)
    index: list[str] = json.loads(raw) if raw else []
    agents = []
    now = time.time()

    for agent_id in index:
        raw_rec = await mem.get(_PREFIX + agent_id)
        if not raw_rec:
            continue
        record = json.loads(raw_rec)

        # Auto-retire stale agents
        last_hb = record.get("last_hb")
        if last_hb and record["status"] not in ("retired", "error"):
            age = now - float(last_hb)
            if age > RETIRE_TTL:
                record["status"] = "retired"
                record["retired_at"] = now
                record["retire_reason"] = "heartbeat_timeout"
                await mem.set(_PREFIX + agent_id, json.dumps(record))
                # Decrement active counter so concurrency cap stays accurate
                raw_count = await mem.get("agents:active:count")
                if raw_count:
                    new_count = max(0, int(raw_count) - 1)
                    await mem.set("agents:active:count", str(new_count))
            elif age > HEARTBEAT_TTL:
                record["status"] = "idle"
                await mem.set(_PREFIX + agent_id, json.dumps(record))

        if not include_retired and record["status"] == "retired":
            continue
        agents.append(record)

    return agents


async def agent_count(mem) -> dict[str, int]:
    """Return counts by status."""
    agents = await agent_registry(mem, include_retired=True)
    counts: dict[str, int] = {}
    for a in agents:
        s = a.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts
