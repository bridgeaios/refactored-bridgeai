"""
test_gap_modules.py — Tests for gaps 12–25 implementation.

Covers: idempotency, clock, cost, constraints, lifecycle, compliance,
        and the /observe/* API endpoints.
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock


# ── In-memory MemoryStore stub for unit tests ──────────────────────────────

class MemStub:
    """Minimal async key-value store backed by a dict."""
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value

    async def delete(self, key):
        self._store.pop(key, None)
        return True

    async def setnx(self, key, value):
        if key not in self._store:
            self._store[key] = value
            return True
        return False

    async def incr(self, key):
        val = int(self._store.get(key) or 0) + 1
        self._store[key] = val
        return val


# ── Gap 13: Clock ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestClock:
    def test_current_cycle_positive(self):
        from app.core.clock import current_cycle
        assert current_cycle() >= 0

    def test_cycle_info_keys(self):
        from app.core.clock import cycle_info
        info = cycle_info()
        for key in ("cycle", "window", "settling", "cycle_start", "cycle_end", "now_sast", "elapsed_s", "remaining_s"):
            assert key in info

    def test_window_is_valid(self):
        from app.core.clock import current_window, CycleWindow
        w = current_window()
        assert w in list(CycleWindow)

    def test_stamp_has_required_keys(self):
        from app.core.clock import stamp
        s = stamp()
        assert "ts" in s and "cycle" in s and "win" in s

    def test_cycle_boundaries_contiguous(self):
        from app.core.clock import cycle_start_ts, cycle_end_ts
        cycle = 100
        assert cycle_end_ts(cycle) == cycle_start_ts(cycle + 1)

    def test_elapsed_plus_remaining_approx_day(self):
        from app.core.clock import cycle_info
        info = cycle_info()
        total = info["elapsed_s"] + info["remaining_s"]
        assert 86390 < total < 86410  # ±10s tolerance


# ── Gap 12: Idempotency ────────────────────────────────────────────────────

@pytest.mark.unit
class TestIdempotency:
    @pytest.mark.asyncio
    async def test_guard_first_call(self):
        from app.core.idempotency import idempotency_guard
        mem = MemStub()
        async with idempotency_guard(mem, "op:001") as g:
            assert not g.already_committed
            await g.commit({"ok": True})

    @pytest.mark.asyncio
    async def test_guard_replay_on_duplicate(self):
        from app.core.idempotency import idempotency_guard
        mem = MemStub()
        async with idempotency_guard(mem, "op:002") as g:
            await g.commit({"value": 42})

        async with idempotency_guard(mem, "op:002") as g2:
            assert g2.already_committed
            assert g2.result["value"] == 42

    @pytest.mark.asyncio
    async def test_guard_fail_increments_attempt(self):
        from app.core.idempotency import idempotency_guard
        import json
        mem = MemStub()
        try:
            async with idempotency_guard(mem, "op:003") as g:
                raise ValueError("simulated failure")
        except ValueError:
            pass
        raw = await mem.get("idempotency:op:003")
        record = json.loads(raw)
        assert record["status"] == "failed"
        assert record["attempt"] == 1

    @pytest.mark.asyncio
    async def test_dlq_push_and_list(self):
        from app.core.idempotency import dlq_push, dlq_list
        mem = MemStub()
        await dlq_push(mem, "op:fail", "timeout", 5)
        entries = await dlq_list(mem)
        assert len(entries) == 1
        assert entries[0]["key"] == "op:fail"

    @pytest.mark.asyncio
    async def test_dlq_retry_removes_entry(self):
        from app.core.idempotency import dlq_push, dlq_list, dlq_retry
        mem = MemStub()
        await dlq_push(mem, "op:retry", "err", 5)
        ok = await dlq_retry(mem, "op:retry")
        assert ok is True
        entries = await dlq_list(mem)
        assert len(entries) == 0

    def test_retry_delay_exponential(self):
        from app.core.idempotency import retry_delay
        assert retry_delay(0) == 1    # 2^0
        assert retry_delay(3) == 8    # 2^3
        assert retry_delay(10) == 300  # capped at 300


# ── Gap 14: Cost Accounting ────────────────────────────────────────────────

@pytest.mark.unit
class TestCostAccounting:
    @pytest.mark.asyncio
    async def test_record_cost_stores_entry(self):
        from app.core.cost import record_cost, cost_recent
        mem = MemStub()
        entry = await record_cost(mem, channel="J", label="test_task", amount=0.5)
        assert entry["channel"] == "J"
        assert entry["amount"] == 0.5
        recent = await cost_recent(mem, limit=10)
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_cost_summary_aggregates_by_channel(self):
        from app.core.cost import record_cost, cost_summary
        mem = MemStub()
        await record_cost(mem, channel="J", label="a", amount=1.0)
        await record_cost(mem, channel="J", label="b", amount=2.0)
        await record_cost(mem, channel="X", label="c", amount=0.5)
        summary = await cost_summary(mem)
        assert summary["totals"]["J"] == pytest.approx(3.0, abs=1e-5)
        assert summary["totals"]["X"] == pytest.approx(0.5, abs=1e-5)

    @pytest.mark.asyncio
    async def test_budget_ok_under_cap(self):
        from app.core.cost import cost_budget_ok
        mem = MemStub()
        ok = await cost_budget_ok(mem, channel="J", proposed=1.0)
        assert ok is True

    @pytest.mark.asyncio
    async def test_budget_not_ok_over_cap(self):
        from app.core.cost import record_cost, cost_budget_ok
        mem = MemStub()
        # J cap = 100 — fill it
        await record_cost(mem, channel="J", label="fill", amount=99.0)
        ok = await cost_budget_ok(mem, channel="J", proposed=5.0)
        assert ok is False


# ── Gap 15: Constraints ────────────────────────────────────────────────────

@pytest.mark.unit
class TestConstraints:
    @pytest.mark.asyncio
    async def test_no_constraint_clean_state(self):
        from app.core.constraints import check_constraints
        mem = MemStub()
        result = await check_constraints(mem, channel="J", action="task")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_queue_depth_blocks_jobs(self):
        from app.core.constraints import check_constraints
        mem = MemStub()
        await mem.set("tasks:pending:count", "501")
        result = await check_constraints(mem, channel="J", action="task")
        assert result.ok is False
        assert result.constraint == "LOAD"

    @pytest.mark.asyncio
    async def test_agent_concurrency_blocks_agents(self):
        from app.core.constraints import check_constraints
        mem = MemStub()
        await mem.set("agents:active:count", "11")
        result = await check_constraints(mem, channel="X", action="inference")
        assert result.ok is False
        assert result.constraint == "AGENT"

    @pytest.mark.asyncio
    async def test_treasury_floor_blocks_payouts(self):
        from app.core.constraints import check_constraints
        mem = MemStub()
        await mem.set("treasury:brdg:total", "5.0")  # below 10 BRDG floor
        result = await check_constraints(mem, channel="F", action="payout")
        assert result.ok is False
        assert result.constraint == "BALANCE"

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_cap(self):
        from app.core.constraints import check_constraints
        import json
        mem = MemStub()
        # Exhaust the F:payout rate limit (5/min)
        now = time.time()
        calls = [now - i for i in range(5)]
        await mem.set("ratelimit:F:payout", json.dumps(calls))
        result = await check_constraints(mem, channel="F", action="payout")
        assert result.ok is False
        assert result.constraint == "RATE"


# ── Gap 19: Agent Lifecycle ────────────────────────────────────────────────

@pytest.mark.unit
class TestAgentLifecycle:
    @pytest.mark.asyncio
    async def test_register_agent(self):
        from app.core.lifecycle import register_agent, agent_registry
        mem = MemStub()
        agent_id = await register_agent(mem, name="test_agent", channel="X")
        assert "test_agent" in agent_id
        agents = await agent_registry(mem)
        assert any(a["id"] == agent_id for a in agents)

    @pytest.mark.asyncio
    async def test_heartbeat_marks_active(self):
        from app.core.lifecycle import register_agent, heartbeat, agent_registry
        mem = MemStub()
        agent_id = await register_agent(mem, name="hb_agent", channel="J")
        await heartbeat(mem, agent_id, meta={"tasks": 5})
        agents = await agent_registry(mem)
        agent = next(a for a in agents if a["id"] == agent_id)
        assert agent["status"] == "active"
        assert agent["meta"]["tasks"] == 5

    @pytest.mark.asyncio
    async def test_retire_agent(self):
        from app.core.lifecycle import register_agent, retire_agent, agent_registry
        mem = MemStub()
        agent_id = await register_agent(mem, name="retire_agent", channel="F")
        await retire_agent(mem, agent_id, reason="test_done")
        agents = await agent_registry(mem, include_retired=True)
        agent = next(a for a in agents if a["id"] == agent_id)
        assert agent["status"] == "retired"

    @pytest.mark.asyncio
    async def test_stale_agent_auto_retired(self):
        from app.core.lifecycle import register_agent, heartbeat, agent_registry
        import json
        mem = MemStub()
        agent_id = await register_agent(mem, name="stale_agent", channel="X")
        # Manually set last_hb to 400s ago (> RETIRE_TTL=300)
        raw = await mem.get(f"agent:{agent_id}")
        record = json.loads(raw)
        record["last_hb"] = time.time() - 400
        record["status"] = "active"
        await mem.set(f"agent:{agent_id}", json.dumps(record))
        agents = await agent_registry(mem)  # triggers auto-retire
        agent = next((a for a in agents if a["id"] == agent_id), None)
        assert agent is None  # retired agents excluded by default


# ── Gap 25: Compliance ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestCompliance:
    @pytest.mark.asyncio
    async def test_audit_log_creates_entry(self):
        from app.core.compliance import audit_log, audit_recent, AuditEvent
        mem = MemStub()
        eid = await audit_log(mem, AuditEvent.DATA_ACCESS, actor="worker", subject="lead:1")
        entries = await audit_recent(mem)
        assert any(e["id"] == eid for e in entries)

    @pytest.mark.asyncio
    async def test_audit_log_is_append_only(self):
        from app.core.compliance import audit_log, audit_recent, AuditEvent
        mem = MemStub()
        await audit_log(mem, AuditEvent.ADMIN_ACTION, actor="admin", subject="system")
        await audit_log(mem, AuditEvent.AUTH_SUCCESS, actor="user:1", subject="login")
        entries = await audit_recent(mem)
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_consent_grant_and_check(self):
        from app.core.compliance import consent_grant, consent_check
        mem = MemStub()
        await consent_grant(mem, user_id="user:42", purpose="marketing")
        ok = await consent_check(mem, user_id="user:42", purpose="marketing")
        assert ok is True

    @pytest.mark.asyncio
    async def test_consent_denied_without_grant(self):
        from app.core.compliance import consent_check
        mem = MemStub()
        ok = await consent_check(mem, user_id="user:99", purpose="analytics")
        assert ok is False

    @pytest.mark.asyncio
    async def test_consent_revoke(self):
        from app.core.compliance import consent_grant, consent_revoke, consent_check
        mem = MemStub()
        await consent_grant(mem, user_id="user:5", purpose="crm")
        await consent_revoke(mem, user_id="user:5", purpose="crm")
        ok = await consent_check(mem, user_id="user:5", purpose="crm")
        assert ok is False

    @pytest.mark.asyncio
    async def test_pii_tag(self):
        from app.core.compliance import tag_pii, PIIClass, retention_due
        mem = MemStub()
        await tag_pii(mem, record_id="lead:10", fields=["email"], pii_class=PIIClass.EMAIL)
        due = await retention_due(mem, "lead:10")
        assert due is False  # freshly tagged, not expired


# ── Observability API endpoints ────────────────────────────────────────────

@pytest.fixture
def auth_client(client):
    """Client fixture with JWT dependency overridden to bypass auth."""
    from app.main import app
    from app.domains.infra.deps import require_jwt
    app.dependency_overrides[require_jwt] = lambda: {"sub": "test", "authority": "test"}
    yield client
    app.dependency_overrides.pop(require_jwt, None)


@pytest.mark.unit
class TestObservabilityEndpoints:
    async def test_clock_endpoint(self, auth_client):
        r = await auth_client.get("/api/observe/clock")
        assert r.status_code == 200
        data = r.json()
        assert "cycle" in data
        assert "window" in data

    async def test_health_endpoint(self, auth_client):
        r = await auth_client.get("/api/observe/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_topology_endpoint(self, auth_client):
        r = await auth_client.get("/api/observe/topology")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0

    async def test_incentives_endpoint(self, auth_client):
        r = await auth_client.get("/api/observe/incentives")
        assert r.status_code == 200
        data = r.json()
        assert "treasury_split" in data
        assert "channel_weights" in data

    async def test_summary_endpoint(self, auth_client):
        r = await auth_client.get("/api/observe/summary")
        assert r.status_code == 200
        data = r.json()
        for key in ("clock", "costs", "constraints", "agents", "dlq_count", "compliance"):
            assert key in data

    async def test_dlq_endpoint_empty(self, auth_client):
        r = await auth_client.get("/api/observe/dlq")
        assert r.status_code == 200
        assert r.json()["count"] == 0
