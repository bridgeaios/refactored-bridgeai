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

    # Treasury service accesses _engine directly for idempotency checks
    _engine_mock = MagicMock()
    _engine_mock.claim_idempotency = AsyncMock(return_value=True)
    mock._engine = _engine_mock

    return mock


@pytest.fixture
async def client(mock_memory) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.core.deps import get_memory
    from app.core.control_plane import TREASURY_GATE
    from app.domains.infra.deps import require_jwt

    _fake_claims = {"sub": "0xtest", "address": "0xtest", "authority": "test"}

    # Override get_memory so all Depends(get_memory) calls receive the mock.
    app.dependency_overrides[get_memory] = lambda: mock_memory
    # Bypass JWT so business logic tests are not blocked by auth.
    app.dependency_overrides[require_jwt] = lambda: _fake_claims
    # Unlock the treasury gate so financial endpoints can be tested.
    TREASURY_GATE.unlock()

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_memory, None)
    app.dependency_overrides.pop(require_jwt, None)
    TREASURY_GATE.lock("Test teardown — control plane not yet run")


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
