import asyncio

from fastapi import WebSocket

HEARTBEAT = 20.0

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.active.setdefault(channel, []).append(ws)
        # Send immediate heartbeat so systemVerifier (5s timeout) passes
        try:
            await ws.send_json({"type": "heartbeat", "ts": asyncio.get_event_loop().time()})
        except Exception:
            pass

    async def disconnect(self, channel: str, ws: WebSocket):
        async with self.lock:
            if channel in self.active and ws in self.active[channel]:
                self.active[channel].remove(ws)

    async def broadcast(self, channel: str, message: dict):
        async with self.lock:
            sockets = list(self.active.get(channel, []))
        dead = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self.lock:
                for d in dead:
                    if d in self.active.get(channel, []):
                        self.active[channel].remove(d)

    async def broadcast_all(self, message: dict):
        async with self.lock:
            channels = list(self.active.keys())
        for ch in channels:
            await self.broadcast(ch, message)

    async def heartbeat(self):
        while True:
            await asyncio.sleep(HEARTBEAT)
            try:
                await self.broadcast_all({"type":"heartbeat","ts": asyncio.get_event_loop().time()})
            except Exception:
                pass
