"""
WebSocket connection manager with Redis pub/sub backend.

Two modes:
  - Redis available  → pub/sub via aioredis; messages cross processes/instances
  - Redis missing    → in-memory broadcast (single process, dev fallback)

External code calls:
    manager.broadcast(channel, message)   → publishes to Redis or in-memory
    manager.broadcast_all(message)        → publishes to "__all__" channel
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)

HEARTBEAT = 20.0
_ALL_CHANNEL = "__all__"


class ConnectionManager:
    def __init__(self) -> None:
        # Local WebSocket connections keyed by channel
        self.active: dict[str, list[WebSocket]] = {}
        self.lock = asyncio.Lock()

        # Redis pub/sub state (populated by _start_redis if available)
        self._redis_pub: Any = None   # aioredis client for publishing
        self._redis_task: asyncio.Task | None = None
        self._redis_enabled = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Call once at app startup (lifespan). Attempts Redis connection."""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis.asyncio as aioredis  # type: ignore[import]
            client = aioredis.from_url(redis_url, decode_responses=True)
            await client.ping()
            self._redis_pub = client
            self._redis_enabled = True
            # Start subscriber loop via safe_spawn so the control plane tracks it
            from app.core.safe_spawn import safe_spawn
            self._redis_task = safe_spawn(
                self._redis_subscriber(redis_url), name="ws-redis-subscriber"
            )
            log.info("WebSocket hub: Redis pub/sub active (%s)", redis_url)
        except Exception as exc:
            log.warning("WebSocket hub: Redis unavailable (%s) — using in-memory broadcast", exc)

    async def shutdown(self) -> None:
        if self._redis_task:
            self._redis_task.cancel()
        if self._redis_pub:
            await self._redis_pub.aclose()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.active.setdefault(channel, []).append(ws)
        try:
            await ws.send_json({"type": "heartbeat", "ts": asyncio.get_event_loop().time()})
        except Exception:
            pass

    async def disconnect(self, channel: str, ws: WebSocket) -> None:
        async with self.lock:
            bucket = self.active.get(channel, [])
            if ws in bucket:
                bucket.remove(ws)

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast(self, channel: str, message: dict) -> None:
        """Publish to Redis (cross-process) or fall back to in-memory."""
        if self._redis_enabled and self._redis_pub:
            try:
                await self._redis_pub.publish(
                    f"ws:{channel}", json.dumps(message)
                )
                return
            except Exception as exc:
                log.warning("Redis publish failed, falling back to in-memory: %s", exc)
        await self._local_broadcast(channel, message)

    async def broadcast_all(self, message: dict) -> None:
        await self.broadcast(_ALL_CHANNEL, message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _local_broadcast(self, channel: str, message: dict) -> None:
        """Send to WebSocket connections in THIS process only."""
        async with self.lock:
            targets = list(self.active.get(channel, []))
            if channel != _ALL_CHANNEL:
                # Also deliver to subscribers of the __all__ meta-channel
                targets += list(self.active.get(_ALL_CHANNEL, []))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self.lock:
                for d in dead:
                    for bucket in self.active.values():
                        if d in bucket:
                            bucket.remove(d)

    async def _redis_subscriber(self, redis_url: str) -> None:
        """Long-running task: subscribe to all ws:* channels and fan-out locally."""
        import redis.asyncio as aioredis  # type: ignore[import]
        sub_client = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = sub_client.pubsub()
        await pubsub.psubscribe("ws:*")
        log.info("WebSocket hub: subscribed to Redis pattern ws:*")
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "pmessage":
                    continue
                redis_channel: str = raw["channel"]           # e.g. "ws:treasury"
                channel = redis_channel.removeprefix("ws:")   # e.g. "treasury"
                try:
                    message = json.loads(raw["data"])
                except Exception:
                    continue
                # Fan out to local connections on this channel + __all__
                await self._local_broadcast(channel, message)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.punsubscribe("ws:*")
            await sub_client.aclose()

    async def heartbeat(self) -> None:
        """Periodic heartbeat to all connected clients."""
        while True:
            await asyncio.sleep(HEARTBEAT)
            try:
                await self.broadcast_all(
                    {"type": "heartbeat", "ts": asyncio.get_event_loop().time()}
                )
            except Exception:
                pass
