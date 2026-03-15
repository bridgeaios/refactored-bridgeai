from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "Bridge AI OS API"
    assert "docs" in data
    assert "health" in data


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_mission_board():
    r = client.get("/api/mission/board")
    assert r.status_code == 200
    data = r.json()
    assert all(k in data for k in ("backlog", "in_progress", "review", "done"))


def test_state_mutation_ok():
    r = client.post("/api/state", json={"reducer": "emotionOverride", "payload": {"valenceDelta": 0.05}, "authToken": "internal"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "data" in data or "broadcast" in data.get("data", {})


def test_state_mutation_reducer_required():
    r = client.post("/api/state", json={"payload": {}})
    assert r.status_code == 400


def test_state_mutation_unsanctioned_reducer():
    """Strict mode: unsanctioned reducers rejected."""
    r = client.post("/api/state", json={"reducer": "rogueReducer", "payload": {}, "authToken": "internal"})
    assert r.status_code == 400
    assert "not sanctioned" in r.json().get("detail", "")


def test_add_skill():
    r = client.post("/api/skills", json={"name": "Test Skill", "tags": ["test", "api"]})
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_add_skill_validation():
    r = client.post("/api/skills", json={"name": "NoTags"})
    assert r.status_code == 422


def test_emotion_compute():
    r = client.post("/api/emotion/compute", json={"votes": 1, "backlog": 0, "in_progress": 1, "sentiment": 0.5})
    assert r.status_code == 200
    data = r.json()
    assert "state" in data or "inputs" in data


def test_ubi_claim():
    r = client.post("/api/ubi/claim", json={"address": "0xTest123"})
    assert r.status_code == 200
    data = r.json()
    assert "amount" in data
    assert data["amount"] >= 0


def test_ubi_claim_no_address():
    r = client.post("/api/ubi/claim", json={})
    assert r.status_code == 400


def test_marketplace_create_and_get():
    r = client.post("/api/marketplace/task", json={"title": "Test Task", "reward": 10})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "created"
    task_id = data.get("task", {}).get("id")
    r2 = client.get("/api/marketplace/tasks")
    assert r2.status_code == 200
    tasks = r2.json()
    assert any(t.get("id") == task_id for t in tasks)


def test_marketplace_accept():
    # Create task first
    r = client.post("/api/marketplace/task", json={"title": "Accept Me", "reward": 5})
    assert r.status_code == 200
    task_id = r.json().get("task", {}).get("id")
    r2 = client.post("/api/marketplace/accept", json={"task_id": task_id, "wallet": "0xAcceptor"})
    assert r2.status_code == 200
    assert r2.json().get("status") == "accepted"


def test_marketplace_accept_missing_fields():
    r = client.post("/api/marketplace/accept", json={"task_id": 999})
    assert r.status_code == 400


def test_tts_text_required():
    r = client.post("/api/tts", json={})
    assert r.status_code == 400


def test_train_status():
    r = client.get("/api/train/status")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data or "started" in data or isinstance(data, dict)


def test_sdg_metrics():
    r = client.get("/api/sdg/metrics")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_revenue_status():
    r = client.get("/api/revenue/status")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_audit_drift():
    """Drift detection — immune system logic."""
    r = client.get("/api/audit/drift")
    assert r.status_code == 200
    data = r.json()
    assert "drift_score" in data
    assert "threshold" in data
    assert "should_trigger_governance" in data
    assert "mission_board" in data
    assert 0 <= data["drift_score"] <= 1


def test_twin_evolve_requires_orchestrator():
    """Evolution requires orchestrator auth + evolution budget."""
    r = client.post("/api/twin/evolve", json={"feedback": "test"})
    assert r.status_code == 200
    data = r.json()
    # Without authToken, authority is public → evolution denied
    err = data.get("data", {}).get("error", "") or data.get("error", "")
    assert data.get("ok") is False or "orchestrator" in str(err).lower() or "evolution" in str(err).lower()


def test_telemetry_includes_evolution_budget():
    """Telemetry exposes evolution_budget_remaining."""
    r = client.get("/api/telemetry")
    assert r.status_code == 200
    data = r.json()
    body = data.get("data", data)
    assert "evolution_budget_remaining" in body


def test_state_snapshot():
    """State snapshot returns state, state_version, state_hash."""
    r = client.get("/api/state/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "state" in data
    assert "state_version" in data
    assert "state_hash" in data
    assert "mission_board" in data["state"]


def test_health_extended():
    """Extended health returns composite health score."""
    r = client.get("/api/health/extended")
    assert r.status_code == 200
    data = r.json()
    assert "health_score" in data
    assert "components" in data
    assert 0 <= data["health_score"] <= 1


def test_root_includes_identity_hash():
    """Identity seal exposed in root. Prevents silent mutation of purpose."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "identity_hash" in data
    assert "reducer_identity_hash" in data


def test_twin_decide_includes_deterministic_seed():
    """Determinism with replay: seed + state_version in meta."""
    r = client.post("/api/twin/decide", json={
        "environment": {},
        "candidates": [{"action": "a", "expected_value": 0.5}, {"action": "b", "expected_value": 0.3}],
    })
    assert r.status_code == 200
    data = r.json()
    meta = data.get("meta", {})
    assert "deterministic_seed" in meta or "state_version" in meta


def test_telemetry_includes_degradation_and_drift():
    """Telemetry: degradation_level, event_backlog_depth, baseline_drift."""
    r = client.get("/api/telemetry")
    assert r.status_code == 200
    body = r.json().get("data", r.json())
    assert "degradation_level" in body
    assert "event_backlog_depth" in body
    assert "baseline_drift" in body


def test_replication_status():
    """Replication engine status: enabled, twin_count, open_tasks, rules_evaluated."""
    r = client.get("/api/replication/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "twin_count" in data
    assert "open_tasks" in data
    assert "capacity" in data


def test_replication_nodes():
    """Node discovery: list registered nodes."""
    r = client.get("/api/replication/nodes")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "nodes" in data
    assert isinstance(data["nodes"], list)


def test_replication_register():
    """Register a node for mesh discovery."""
    r = client.post("/api/replication/register", json={"node_id": "test-node-1", "url": "http://localhost:8000"})
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert r.json().get("node_id") == "test-node-1"


def test_replication_register_missing_fields():
    r = client.post("/api/replication/register", json={"node_id": "x"})
    assert r.status_code == 400


def test_physics_cohesion_capability_off():
    """
    Physics cohesion: core still functions when speech, economy, evolution disabled.
    If yes → physics are modular. If no → hidden coupling exists.
    """
    import os
    orig = {}
    for k in ("BRIDGE_CAP_SPEECH", "BRIDGE_CAP_UBI", "BRIDGE_CAP_TRADE", "BRIDGE_CAP_EVOLUTION"):
        orig[k] = os.environ.pop(k, None)
    try:
        os.environ["BRIDGE_CAP_SPEECH"] = "0"
        os.environ["BRIDGE_CAP_UBI"] = "0"
        os.environ["BRIDGE_CAP_TRADE"] = "0"
        os.environ["BRIDGE_CAP_EVOLUTION"] = "0"
        r = client.get("/api/health")
        assert r.status_code == 200
        r2 = client.get("/")
        assert r2.status_code == 200
        r3 = client.get("/api/mission/board")
        assert r3.status_code == 200
        r4 = client.get("/api/twin/profile")
        assert r4.status_code == 200
    finally:
        for k, v in orig.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]
