import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestHealthEndpoint:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


@pytest.mark.unit
class TestRootEndpoint:
    async def test_root(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


@pytest.mark.unit
class TestCapabilitiesEndpoint:
    async def test_capabilities(self, client: AsyncClient):
        response = await client.get("/api/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "data" in data


@pytest.mark.unit
class TestStateEndpoints:
    async def test_state_reducers(self, client: AsyncClient):
        response = await client.get("/api/state/reducers")
        assert response.status_code == 200

    async def test_state_mutation_requires_reducer(self, client: AsyncClient):
        response = await client.post("/api/state", json={})
        assert response.status_code == 400

    async def test_state_mutation_requires_payload(self, client: AsyncClient):
        response = await client.post("/api/state", json={"reducer": "test"})
        assert response.status_code in [400, 403]


@pytest.mark.unit
class TestTelemetryEndpoint:
    async def test_telemetry(self, client: AsyncClient):
        response = await client.get("/api/telemetry")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
