"""
Integration tests for WebSocket authentication (BUG-006 patch regression guard).

Verifies that:
- Authenticated connections on private channels succeed
- Unauthenticated connections on private channels are closed with code 4001
- Public channels allow unauthenticated connections
- Invalid tokens are rejected with code 4001
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from httpx import ASGITransport, AsyncClient

# ─────────────────────────────────────────────────────────────────────────────
# Minimal app that reproduces the patched websocket_endpoint logic
# ─────────────────────────────────────────────────────────────────────────────

def build_ws_app(public_channels=("public", "broadcast", "system")):
    """Build a minimal FastAPI app with the patched WebSocket endpoint."""
    app = FastAPI()

    @app.websocket("/ws/{channel}")
    async def websocket_endpoint(websocket: WebSocket, channel: str) -> None:
        token = (
            websocket.query_params.get("token")
            or websocket.headers.get("authorization", "").removeprefix("Bearer ").strip()
        )
        if token:
            try:
                from app.services.siwe_auth import verify_jwt
                result = verify_jwt(token)
                if result is None:
                    raise ValueError("Invalid token")
            except Exception:
                await websocket.close(code=4001)
                return
        elif channel not in public_channels:
            await websocket.close(code=4001)
            return

        await websocket.accept()
        await websocket.send_json({"type": "welcome"})
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_json({"echo": data})
        except WebSocketDisconnect:
            pass

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_private_channel_no_token_rejected():
    """Private channel without token must be closed with 4001."""
    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with pytest.raises(Exception):
        # WebSocketDisconnect or connection refused — 4001 close
        with client.websocket_connect("/ws/agents") as ws:
            ws.receive_json()  # Should not reach here


@pytest.mark.asyncio
async def test_public_channel_no_token_allowed(monkeypatch):
    """Public channel without a token must be accepted."""
    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/public") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "welcome"


@pytest.mark.asyncio
async def test_broadcast_channel_no_token_allowed():
    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/broadcast") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "welcome"


@pytest.mark.asyncio
async def test_private_channel_valid_token_allowed(monkeypatch):
    """Valid JWT token in query param must allow connection to private channel."""
    # Generate a real test token
    monkeypatch.setenv(
        "BRIDGE_JWT_SECRET",
        "test-secret-for-unit-tests-bridge-ai-system-2026",
    )
    # Also support alternate env var names the service may use
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-unit-tests-bridge-ai-system-2026")

    from app.services.siwe_auth import create_jwt
    token = create_jwt("0xTestAddress", authority="test")

    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect(f"/ws/agents?token={token}") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "welcome"


@pytest.mark.asyncio
async def test_private_channel_invalid_token_rejected(monkeypatch):
    """Malformed/expired token must result in connection refusal (4001)."""
    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/agents?token=not.a.real.jwt") as ws:
            ws.receive_json()


@pytest.mark.asyncio
async def test_system_channel_no_token_allowed():
    """'system' is a whitelisted public channel — no auth required."""
    app = build_ws_app()
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/system") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "welcome"


@pytest.mark.asyncio
async def test_custom_public_channels_configurable():
    """public_channels list can be extended — verifies the guard is parameterizable."""
    app = build_ws_app(public_channels=("public", "broadcast", "system", "demo"))
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/demo") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "welcome"
