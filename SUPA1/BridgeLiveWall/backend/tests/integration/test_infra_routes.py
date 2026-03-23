import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.errors import BridgeError, NetworkError, error_response
from app.domains.infra.deps import get_infra
from app.domains.infra.router import router as infra_router
from app.domains.infra.services import InfraServices


def _make_mock_infra():
    m = MagicMock(spec=InfraServices)
    m.verify_siwe = AsyncMock(
        return_value={"ok": True, "data": {"token": "test-token"}, "meta": {}}
    )
    m.mem_get = AsyncMock(return_value=None)
    m.mem_set = AsyncMock(return_value=True)
    m.google_sheets_available = MagicMock(return_value=False)
    m.youtube_available = MagicMock(return_value=False)
    m.youtube_search = AsyncMock(return_value={"ok": True, "results": []})
    return m


@pytest.fixture
def mock_infra():
    return _make_mock_infra()


def _register_bridge_errors(app: FastAPI) -> None:
    status_map = {
        "NOT_FOUND": 404,
        "VALIDATION_ERROR": 422,
        "ECONOMIC_GATE_ERROR": 402,
        "AUTH_ERROR": 401,
        "NETWORK_ERROR": 503,
    }

    @app.exception_handler(BridgeError)
    async def _h(_, exc: BridgeError):
        code = status_map.get(exc.code, 500)
        return JSONResponse(status_code=code, content=error_response(exc))


@pytest.fixture
async def client(mock_infra):
    app = FastAPI()
    _register_bridge_errors(app)
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
async def test_siwe_login(client, mock_infra):
    resp = await client.post(
        "/auth/login",
        json={"message": "test msg", "signature": "0xsig", "address": "0x0000000000000000000000000000000000000000"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_infra.verify_siwe.assert_called_once()


@pytest.mark.asyncio
async def test_skills_youtube_search_503_when_unavailable(client, mock_infra):
    mock_infra.youtube_search = AsyncMock(side_effect=NetworkError("unavailable"))
    resp = await client.get("/skills/youtube-search?q=python")
    assert resp.status_code == 503
