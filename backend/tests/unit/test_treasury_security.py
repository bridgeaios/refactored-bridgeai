"""
Unit tests for treasury security guards.

Regression guard for:
- BUG-004: ENV=local bypass must NOT grant treasury write access
- CFO_TOKEN mechanism must work correctly
- BRIDGE_ALLOW_TREASURY_WRITES flag must work correctly
- Disabled state when no config present
"""
from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest


def _load_writes_allowed():
    """Import the guard function fresh (avoids module-level caching of env vars)."""
    import app.domains.economy.router as m
    importlib.reload(m)
    return m._treasury_writes_allowed


# ─────────────────────────────────────────────────────────────────────────────
# BUG-004 regression: ENV=local must NOT bypass treasury writes
# ─────────────────────────────────────────────────────────────────────────────

def test_env_local_does_not_bypass_treasury(monkeypatch):
    """BUG-004: setting ENV=local must not grant write access."""
    monkeypatch.setenv("ENV", "local")
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is False, f"BUG-004 regression: ENV=local granted access via reason='{reason}'"


def test_env_development_does_not_bypass_treasury(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is False


def test_node_env_local_does_not_bypass_treasury(monkeypatch):
    monkeypatch.setenv("NODE_ENV", "local")
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is False


# ─────────────────────────────────────────────────────────────────────────────
# Disabled when no config present
# ─────────────────────────────────────────────────────────────────────────────

def test_treasury_disabled_with_no_config(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is False
    assert reason == "disabled"


# ─────────────────────────────────────────────────────────────────────────────
# BRIDGE_ALLOW_TREASURY_WRITES flag
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("flag_value", ["1", "true", "yes", "on", "True", "YES"])
def test_allow_flag_grants_access(monkeypatch, flag_value):
    monkeypatch.setenv("BRIDGE_ALLOW_TREASURY_WRITES", flag_value)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is True
    assert reason == "allow_flag"


@pytest.mark.parametrize("bad_value", ["0", "false", "no", "off", "", "FALSE"])
def test_allow_flag_false_denies_access(monkeypatch, bad_value):
    monkeypatch.setenv("BRIDGE_ALLOW_TREASURY_WRITES", bad_value)
    monkeypatch.delenv("CFO_TOKEN", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn()
    assert allowed is False


# ─────────────────────────────────────────────────────────────────────────────
# CFO_TOKEN mechanism
# ─────────────────────────────────────────────────────────────────────────────

def test_cfo_token_correct_header_grants_access(monkeypatch):
    monkeypatch.setenv("CFO_TOKEN", "super-secret-cfo-token")
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)

    from unittest.mock import MagicMock
    mock_request = MagicMock()
    mock_request.headers.get = lambda k, d="": "super-secret-cfo-token" if "cfo" in k.lower() else d

    fn = _load_writes_allowed()
    allowed, reason = fn(request=mock_request)
    assert allowed is True
    assert reason == "token"


def test_cfo_token_wrong_header_denies_access(monkeypatch):
    monkeypatch.setenv("CFO_TOKEN", "super-secret-cfo-token")
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)

    from unittest.mock import MagicMock
    mock_request = MagicMock()
    mock_request.headers.get = lambda k, d="": "wrong-token" if "cfo" in k.lower() else d

    fn = _load_writes_allowed()
    allowed, reason = fn(request=mock_request)
    assert allowed is False
    assert reason == "token_required"


def test_cfo_token_no_request_denies_access(monkeypatch):
    """CFO_TOKEN set but no request object — cannot verify header, must deny."""
    monkeypatch.setenv("CFO_TOKEN", "super-secret-cfo-token")
    monkeypatch.delenv("BRIDGE_ALLOW_TREASURY_WRITES", raising=False)

    fn = _load_writes_allowed()
    allowed, reason = fn(request=None)
    assert allowed is False
    assert reason == "token_required"
