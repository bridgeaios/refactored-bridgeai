"""Integration tests for bridgeos.tvm (minimal app + X-TVM-Roles)."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.tvm import events as tvm_events
from app.domains.tvm import store as tvm_store
from app.domains.tvm.router import router as tvm_router


def _h(roles: str) -> dict[str, str]:
    return {"X-TVM-Roles": roles}


@pytest.fixture
def tvm_app() -> FastAPI:
    app = FastAPI()
    app.include_router(tvm_router, prefix="/api")
    return app


@pytest.fixture(autouse=True)
def _tvm_reset() -> None:
    tvm_store.reset_store()
    tvm_events.reset_events()
    yield
    tvm_store.reset_store()
    tvm_events.reset_events()


@pytest.fixture
async def tvm_client(tvm_app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=tvm_app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_reader_lists_rows(tvm_client: AsyncClient) -> None:
    r = await tvm_client.get("/api/tvm", headers=_h("tvm.reader"))
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    topics = {row["topic"] for row in data}
    assert "MailPipeline" in topics


@pytest.mark.asyncio
async def test_agent_forbidden_upsert(tvm_client: AsyncClient) -> None:
    body = {
        "topic": "MailPipeline",
        "configured": 1,
        "healthy": 1,
        "degraded": 0,
        "action_required": 0,
        "autofix_available": 0,
        "human_approval_needed": 0,
        "last_updated": 0,
        "recommendation_code": None,
        "signature": None,
    }
    r = await tvm_client.post("/api/tvm/MailPipeline", headers=_h("tvm.agent"), json=body)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_operator_upsert_and_signature_valid(tvm_client: AsyncClient) -> None:
    body = {
        "topic": "MailPipeline",
        "configured": 1,
        "healthy": 1,
        "degraded": 0,
        "action_required": 0,
        "autofix_available": 0,
        "human_approval_needed": 0,
        "last_updated": 0,
        "recommendation_code": None,
        "signature": None,
    }
    r = await tvm_client.post("/api/tvm/MailPipeline", headers=_h("tvm.operator"), json=body)
    assert r.status_code == 200
    j = r.json()
    assert j["healthy"] == 1
    assert j.get("signature")

    v = await tvm_client.get("/api/tvm/meta/signature/MailPipeline", headers=_h("tvm.reader"))
    assert v.status_code == 200
    assert v.json()["valid"] is True


@pytest.mark.asyncio
async def test_proposal_auto_executor_request(tvm_client: AsyncClient) -> None:
    await tvm_client.post(
        "/api/tvm/MailPipeline",
        headers=_h("tvm.operator"),
        json={
            "topic": "MailPipeline",
            "configured": 1,
            "healthy": 0,
            "degraded": 1,
            "action_required": 1,
            "autofix_available": 1,
            "human_approval_needed": 0,
            "last_updated": 0,
            "recommendation_code": None,
            "signature": None,
        },
    )
    pr = await tvm_client.post(
        "/api/tvm/MailPipeline/proposal",
        headers=_h("tvm.agent"),
        json={"recommendation_code": "MP-AF-ROTATE-TOKEN"},
    )
    assert pr.status_code == 200
    ev = tvm_events.recent(20)
    types = [e["event_type"] for e in ev]
    assert "executor.request" in types
    assert "tvm.updated" in types


@pytest.mark.asyncio
async def test_proposal_human_then_approval_emits_executor(tvm_client: AsyncClient) -> None:
    await tvm_client.post(
        "/api/tvm/MailPipeline",
        headers=_h("tvm.operator"),
        json={
            "topic": "MailPipeline",
            "configured": 1,
            "healthy": 0,
            "degraded": 1,
            "action_required": 1,
            "autofix_available": 1,
            "human_approval_needed": 0,
            "last_updated": 0,
            "recommendation_code": None,
            "signature": None,
        },
    )
    tvm_events.reset_events()
    pr = await tvm_client.post(
        "/api/tvm/MailPipeline/proposal",
        headers=_h("tvm.agent"),
        json={"recommendation_code": "MP-HUMAN-ESCALATION"},
    )
    assert pr.status_code == 200
    assert pr.json()["human_approval_needed"] == 1
    mid = tvm_events.recent(50)
    assert not any(e["event_type"] == "executor.request" for e in mid)

    ap = await tvm_client.post(
        "/api/tvm/MailPipeline/approval",
        headers=_h("tvm.operator"),
        json={"approve": True},
    )
    assert ap.status_code == 200
    tail = tvm_events.recent(50)
    assert any(e["event_type"] == "executor.request" for e in tail)


@pytest.mark.asyncio
async def test_executor_result_success_clears_action(tvm_client: AsyncClient) -> None:
    await tvm_client.post(
        "/api/tvm/MailPipeline",
        headers=_h("tvm.operator"),
        json={
            "topic": "MailPipeline",
            "configured": 1,
            "healthy": 0,
            "degraded": 1,
            "action_required": 1,
            "autofix_available": 1,
            "human_approval_needed": 0,
            "last_updated": 0,
            "recommendation_code": "MP-AF-ROTATE-TOKEN",
            "signature": None,
        },
    )
    er = await tvm_client.post(
        "/api/tvm/MailPipeline/executor-result",
        headers=_h("tvm.executor"),
        json={
            "recommendation_code": "MP-AF-ROTATE-TOKEN",
            "status": "success",
            "details": "ok",
            "new_health": 1,
            "new_degraded": 0,
            "correlation_id": "x-1",
        },
    )
    assert er.status_code == 200
    j = er.json()
    assert j["healthy"] == 1
    assert j["action_required"] == 0
    assert j.get("recommendation_code") in (None, "")
