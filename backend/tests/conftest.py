import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_memory():
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    # Treasury relies on append + get_recent for ledger.
    _ledger: list[dict] = []

    async def _append(key, value):
        _ledger.append(value)
        return True

    async def _get_recent(key, limit):
        try:
            lim = int(limit)
        except Exception:
            lim = 50
        return _ledger[-lim:]

    mock.append = AsyncMock(side_effect=_append)
    mock.get_recent = AsyncMock(side_effect=_get_recent)
    return mock


@pytest.fixture
async def client(mock_memory) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    app.dependency_overrides[__import__('app.runtime', fromlist=['memory']).memory] = mock_memory

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_state_data():
    return {
        "reducer": "updateMission",
        "payload": {"title": "Test Mission", "status": "active"},
        "authToken": "test-token"
    }


@pytest.fixture
def sample_websocket_message():
    return {"type": "hello", "channel": "test"}
