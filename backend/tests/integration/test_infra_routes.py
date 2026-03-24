"""
Integration tests for infra domain routes.
Uses httpx.AsyncClient against a minimal app with InfraServices overridden.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.infra.deps import get_infra
from app.domains.infra.router import router as infra_router
from app.domains.infra.services import InfraServices


def _make_mock_infra():
    m = MagicMock(spec=InfraServices)
    m.verify_siwe = AsyncMock(return_value={"ok": True, "token": "test-token", "address": "0xAddr"})
    m.mem_get = AsyncMock(return_value=None)
    m.mem_set = AsyncMock(return_value=True)
    m.google_sheets_available = MagicMock(return_value=False)
    m.youtube_available = MagicMock(return_value=False)
    m.youtube_search = AsyncMock(return_value={"ok": True, "results": []})
    m.youtube_learn = AsyncMock(return_value={"ok": True})
    m.sheets_read = AsyncMock(return_value={"ok": True, "rows": []})
    m.sheets_append = AsyncMock(return_value={"ok": True})
    return m


@pytest.fixture
def mock_infra():
    return _make_mock_infra()


@pytest.fixture
async def client(mock_infra):
    app = FastAPI()
    app.include_router(infra_router)
    app.dependency_overrides[get_infra] = lambda: mock_infra
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_siwe_login(client, mock_infra):
    resp = await client.post(
        "/auth/login",
        json={"message": "test msg", "signature": "0xsig"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_infra.verify_siwe.assert_called_once()


@pytest.mark.asyncio
async def test_siwe_logout(client):
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_youtube_search_503_when_unavailable(client, mock_infra):
    from app.core.errors import NetworkError
    mock_infra.youtube_search = AsyncMock(side_effect=NetworkError("unavailable"))

    # Wire the BridgeError handler so 503 is returned
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from app.core.errors import BridgeError, error_response
    from app.main import _BRIDGE_STATUS_MAP

    app = FastAPI()

    @app.exception_handler(BridgeError)
    async def handler(_req: Request, exc: BridgeError) -> JSONResponse:
        return JSONResponse(status_code=_BRIDGE_STATUS_MAP.get(type(exc), 500), content=error_response(exc))

    app.include_router(infra_router)
    app.dependency_overrides[get_infra] = lambda: mock_infra
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/skills/youtube-search?q=python")
    assert resp.status_code == 503
