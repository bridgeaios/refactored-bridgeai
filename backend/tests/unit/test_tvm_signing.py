"""TVM row signing — canonical JSON + HMAC-SHA256."""
from __future__ import annotations

import os

import pytest

from app.domains.tvm.signing import sign_row, verify_row


@pytest.fixture(autouse=True)
def tvm_signing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_TVM_SIGNING_KEY", "unit-test-tvm-key-at-least-32-characters-long")


def test_sign_verify_roundtrip() -> None:
    row = {
        "topic": "TestTopic",
        "configured": 1,
        "healthy": 0,
        "degraded": 1,
        "action_required": 1,
        "autofix_available": 0,
        "human_approval_needed": 0,
        "last_updated": 123,
        "recommendation_code": None,
        "signature": None,
    }
    row["signature"] = sign_row(row)
    assert verify_row(row) is True


def test_tamper_invalidates_signature() -> None:
    row = {
        "topic": "T",
        "configured": 1,
        "healthy": 1,
        "degraded": 0,
        "action_required": 0,
        "autofix_available": 0,
        "human_approval_needed": 0,
        "last_updated": 1,
        "recommendation_code": None,
        "signature": None,
    }
    row["signature"] = sign_row(row)
    row["healthy"] = 0
    assert verify_row(row) is False


def test_signature_secret_must_match(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "topic": "T",
        "configured": 1,
        "healthy": 1,
        "degraded": 0,
        "action_required": 0,
        "autofix_available": 0,
        "human_approval_needed": 0,
        "last_updated": 1,
        "recommendation_code": None,
        "signature": None,
    }
    monkeypatch.setenv("BRIDGE_TVM_SIGNING_KEY", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    row["signature"] = sign_row(row)
    monkeypatch.setenv("BRIDGE_TVM_SIGNING_KEY", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    assert verify_row(row) is False
