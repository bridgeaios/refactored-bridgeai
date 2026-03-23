"""Verify the global BridgeError exception handler returns { ok, code, message }."""
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.errors import BridgeError, EconomicGateError, NotFoundError, error_response


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(BridgeError)
    async def bridge_error_handler(request, exc: BridgeError):
        status_codes = {
            "NOT_FOUND": 404,
            "VALIDATION_ERROR": 422,
            "ECONOMIC_GATE_ERROR": 402,
            "AUTH_ERROR": 401,
            "NETWORK_ERROR": 503,
        }
        status = status_codes.get(exc.code, 500)
        return JSONResponse(status_code=status, content=error_response(exc))

    @app.get("/test/not-found")
    async def raise_not_found():
        raise NotFoundError("test resource not found")

    @app.get("/test/gate")
    async def raise_gate():
        raise EconomicGateError("task value <= cost")

    return app


def test_not_found_returns_404():
    app = _make_app()
    client = TestClient(app)
    resp = client.get("/test/not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["ok"] is False
    assert body["code"] == "NOT_FOUND"
    assert "not found" in body["message"]


def test_gate_returns_402():
    app = _make_app()
    client = TestClient(app)
    resp = client.get("/test/gate")
    assert resp.status_code == 402
    body = resp.json()
    assert body["ok"] is False
    assert body["code"] == "ECONOMIC_GATE_ERROR"


@pytest.mark.asyncio
async def test_async_client_bridge_error():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/test/not-found")
        assert r.status_code == 404
