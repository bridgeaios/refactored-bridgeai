"""Unit tests for core/errors.py."""
from app.core.errors import (
    AuthError,
    BridgeError,
    EconomicGateError,
    NetworkError,
    NotFoundError,
    ValidationError,
    error_response,
)


def test_bridge_error_is_exception():
    e = BridgeError("base error")
    assert isinstance(e, Exception)
    assert str(e) == "base error"


def test_not_found_is_bridge_error():
    e = NotFoundError("twin not found")
    assert isinstance(e, BridgeError)
    assert e.code == "NOT_FOUND"


def test_validation_error():
    e = ValidationError("invalid amount")
    assert isinstance(e, BridgeError)
    assert e.code == "VALIDATION_ERROR"


def test_economic_gate_error():
    e = EconomicGateError("task value <= cost, rejected")
    assert isinstance(e, BridgeError)
    assert e.code == "ECONOMIC_GATE_ERROR"


def test_auth_error():
    e = AuthError("signature mismatch")
    assert isinstance(e, BridgeError)
    assert e.code == "AUTH_ERROR"


def test_network_error():
    e = NetworkError("node unreachable")
    assert isinstance(e, BridgeError)
    assert e.code == "NETWORK_ERROR"


def test_error_response_shape():
    e = NotFoundError("twin not found")
    resp = error_response(e)
    assert resp == {"ok": False, "code": "NOT_FOUND", "message": "twin not found"}


def test_subclass_preserves_message():
    class CustomError(BridgeError):
        code = "CUSTOM"
    e = CustomError("custom msg")
    assert error_response(e)["message"] == "custom msg"
