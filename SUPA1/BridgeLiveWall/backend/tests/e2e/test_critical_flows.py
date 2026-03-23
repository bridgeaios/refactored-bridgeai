"""
Critical smoke flows against a live server (session autouse conftest).
"""
import pytest
import requests

BASE = "http://127.0.0.1:8001"


@pytest.mark.e2e
def test_flow1_health_check():
    resp = requests.get(f"{BASE}/api/health", timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body or body.get("ok") is True


@pytest.mark.e2e
def test_flow2_treasury_collect():
    resp = requests.post(
        f"{BASE}/api/treasury/collect",
        json={
            "amount": 100.0,
            "currency": "BRDG",
            "source_project": "bridge",
            "method": "internal",
        },
        timeout=10,
    )
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert body.get("ok") is True


@pytest.mark.e2e
def test_flow3_marketplace_open():
    resp = requests.get(f"{BASE}/api/marketplace/open", timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) or isinstance(body.get("tasks"), list)


@pytest.mark.e2e
def test_flow4_twin_decide():
    resp = requests.post(
        f"{BASE}/api/twin/decide",
        json={"prompt": "test decision", "candidates": []},
        timeout=30,
    )
    assert resp.status_code in (200, 201, 422)


@pytest.mark.e2e
def test_flow5_settings_endpoint():
    resp = requests.get(f"{BASE}/api/capabilities", timeout=10)
    assert resp.status_code in (200, 404)
