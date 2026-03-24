"""Unit tests for core/types.py."""
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.types import BridgeBaseModel, ErrorResponse, OkResponse


def test_ok_response_defaults():
    r = OkResponse()
    assert r.ok is True


def test_ok_response_with_data():
    r = OkResponse(data={"amount": 100})
    assert r.data == {"amount": 100}


def test_error_response_shape():
    r = ErrorResponse(code="NOT_FOUND", message="not found")
    assert r.ok is False
    assert r.code == "NOT_FOUND"
    assert r.message == "not found"


def test_bridge_base_model_forbids_extras():
    """All domain models must reject unknown fields."""
    with pytest.raises(PydanticValidationError):
        BridgeBaseModel.model_validate({"unknown_field": "value"})
