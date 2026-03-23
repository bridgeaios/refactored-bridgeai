"""Integration tests — BridgeError exception handler maps to correct HTTP status codes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    AuthError,
    BridgeError,
    EconomicGateError,
    NetworkError,
    NotFoundError,
    ValidationError,
    error_response,
)
from fastapi.responses import JSONResponse
from fastapi import Request


def _make_app(*error_cls_list):
    """Build a minimal FastAPI app with the BridgeError handler and a test route."""
    mini = FastAPI()

    @mini.exception_handler(BridgeError)
    async def handler(_req: Request, exc: BridgeError) -> JSONResponse:
        from app.main import _BRIDGE_STATUS_MAP
        status = _BRIDGE_STATUS_MAP.get(type(exc), 500)
        return JSONResponse(status_code=status, content=error_response(exc))

    for exc_cls in error_cls_list:
        @mini.get(f"/{exc_cls.__name__.lower()}")
        async def _route(cls=exc_cls):
            raise cls("test message")

    return mini


@pytest.mark.parametrize("exc_cls,expected_status", [
    (NotFoundError, 404),
    (ValidationError, 422),
    (EconomicGateError, 402),
    (AuthError, 401),
    (NetworkError, 503),
])
def test_bridge_error_status_codes(exc_cls, expected_status):
    app = _make_app(exc_cls)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/{exc_cls.__name__.lower()}")
    assert resp.status_code == expected_status
    body = resp.json()
    assert body["ok"] is False
    assert body["code"] == exc_cls.code
    assert body["message"] == "test message"


def test_base_bridge_error_returns_500():
    app = _make_app(BridgeError)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/bridgeerror")
    assert resp.status_code == 500
    assert resp.json()["ok"] is False
