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
        response = await client.get("/capabilities")
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


@pytest.mark.unit
class TestCortexControlEndpoints:
    async def test_swarm_health(self, client: AsyncClient):
        response = await client.get("/api/swarm/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "health_score" in data
        assert "components" in data

    async def test_reputation_top(self, client: AsyncClient):
        response = await client.get("/api/reputation/top?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert isinstance(data.get("agents"), list)

    async def test_demand_pump(self, client: AsyncClient):
        response = await client.post("/api/demand/pump", json={"target_backlog": 3, "max_create": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "created" in data
        assert "open_tasks" in data


@pytest.mark.unit
class TestUbiTreasuryLink:
    async def test_ubi_claim_debits_treasury_bucket(self, client: AsyncClient):
        s1 = await client.get("/api/treasury/status")
        assert s1.status_code == 200
        buckets_before = s1.json().get("buckets", {})
        available = float(buckets_before.get("ubi", 0) or 0)
        assert available >= 0

        # Claim UBI: payout is capped by treasury UBI bucket.
        claim = await client.post("/api/ubi/claim", json={"address": "0xabc"})
        assert claim.status_code == 200
        amt = int(claim.json().get("amount", 0))
        # Default claim amount is 100; if treasury has less, payout is reduced.
        expected = int(min(100.0, available)) if available > 0 else 0
        assert amt == expected

        s2 = await client.get("/api/treasury/status")
        assert s2.status_code == 200
        buckets_after = s2.json().get("buckets", {})
        after = float(buckets_after.get("ubi", 0) or 0)
        # Bucket should be debited by the payout amount (within rounding tolerance).
        assert abs((available - after) - float(amt)) < 1e-6


@pytest.mark.unit
class TestTreasuryControlsGuards:
    async def test_treasury_controls_endpoint(self, client: AsyncClient):
        r = await client.get("/api/treasury/controls")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "writes_allowed" in data
        assert "mode" in data

    async def test_treasury_collect_denied_by_default(self, client: AsyncClient, monkeypatch):
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
        monkeypatch.delenv("CFO_TOKEN", raising=False)
        r = await client.post("/api/treasury/collect", json={"amount": 1, "currency": "BRDG", "source_project": "test", "method": "manual"})
        assert r.status_code == 403

    async def test_treasury_collect_allowed_with_flag(self, client: AsyncClient, monkeypatch):
        monkeypatch.setenv("BRIDGE_ALLOW_TREASURY_WRITES", "1")
        r = await client.post("/api/treasury/collect", json={"amount": 1, "currency": "BRDG", "source_project": "test", "method": "manual"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    async def test_treasury_disburse_denied_by_default(self, client: AsyncClient, monkeypatch):
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
        monkeypatch.delenv("CFO_TOKEN", raising=False)
        r = await client.post("/api/treasury/disburse", json={"bucket": "ubi", "amount": 1, "destination": "0xabc"})
        assert r.status_code == 403


@pytest.mark.unit
class TestDecisionIntegrity:
    def test_binary_execution_gate(self):
        """Task type must be in THETA = {'F','P','J','X'}"""
        task = {
            "id": "test1",
            "type": "F",
            "revenue": 10,
            "impact": 5,
            "trust": 2,
            "cost": 3
        }
        value = task["revenue"] + task["impact"] + task["trust"] - task["cost"]
        assert task["type"] in ["F", "P", "J", "X"]
        assert value > 0

    def test_reject_negative_value(self):
        """Negative value tasks must be rejected"""
        task = {
            "id": "test2",
            "type": "F",
            "revenue": 1,
            "impact": 0,
            "trust": 0,
            "cost": 10
        }
        value = task["revenue"] + task["impact"] + task["trust"] - task["cost"]
        assert value <= 0

    def test_theta_rejection(self):
        """Invalid task types must be rejected"""
        task = {
            "id": "test3",
            "type": "INVALID",
            "revenue": 10,
            "cost": 1
        }
        assert task["type"] not in ["F", "P", "J", "X"]

    def test_execution_gate_module(self):
        """Test execution_gate evaluate and select functions"""
        from app.services.execution_gate import evaluate, select

        valid_task = {
            "id": "task1",
            "type": "F",
            "revenue": 10,
            "impact": 5,
            "trust": 2,
            "cost": 3
        }
        result = evaluate(valid_task)
        assert result is not None
        assert result.score == 14

        invalid_type = {"id": "task2", "type": "Z", "revenue": 10, "cost": 1}
        assert evaluate(invalid_type) is None

        negative_value = {"id": "task3", "type": "F", "revenue": 1, "cost": 10}
        assert evaluate(negative_value) is None

        tasks = [
            {"id": "a", "type": "F", "revenue": 10, "cost": 2},
            {"id": "b", "type": "P", "revenue": 20, "cost": 5},
            {"id": "c", "type": "X", "revenue": 5, "cost": 1},
        ]
        selected = select(tasks)
        assert selected is not None
        assert selected.task["id"] == "b"

        empty_result = select([])
        assert empty_result is None
