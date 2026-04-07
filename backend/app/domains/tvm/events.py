"""In-process event bus stub for TVM (replace with Redis/pub-sub)."""
from __future__ import annotations

import time
from collections import deque
from typing import Any

_MAX = 500
_bus: deque[dict[str, Any]] = deque(maxlen=_MAX)


def reset_events() -> None:
    _bus.clear()


def publish(event_type: str, payload: dict[str, Any], *, correlation_id: str = "") -> dict[str, Any]:
    env = {
        "event_type": event_type,
        "version": "1.0",
        "correlation_id": correlation_id,
        "emitted_at": int(time.time()),
        **payload,
    }
    _bus.append(env)
    return env


def recent(limit: int = 50) -> list[dict[str, Any]]:
    n = max(1, min(limit, _MAX))
    return list(_bus)[-n:]
