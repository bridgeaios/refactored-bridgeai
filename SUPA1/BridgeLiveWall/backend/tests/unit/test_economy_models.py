import pytest
from pydantic import ValidationError

from app.domains.economy.models import (
    AcceptTaskRequest,
    CollectRequest,
    CollectResponse,
    CompleteTaskRequest,
    MarketplaceTask,
    PostTaskRequest,
    TreasuryStatus,
    UbiClaimRequest,
)


def test_collect_request_requires_amount():
    with pytest.raises(ValidationError):
        CollectRequest()


def test_collect_request_defaults():
    r = CollectRequest(amount=100.0)
    assert r.currency == "BRDG"
    assert r.method == "internal"
    assert r.source_project == "bridge"


def test_collect_request_rejects_negative():
    with pytest.raises(ValidationError):
        CollectRequest(amount=-1.0)


def test_collect_response_ok():
    r = CollectResponse(ok=True, tx_id="abc123", splits={"ubi": 40.0})
    assert r.ok is True


def test_treasury_status_shape():
    s = TreasuryStatus(total=1000.0, buckets={"ubi": 400.0, "treasury": 300.0})
    assert s.total == 1000.0


def test_ubi_claim_request_requires_address():
    with pytest.raises(ValidationError):
        UbiClaimRequest()


def test_post_task_requires_title():
    with pytest.raises(ValidationError):
        PostTaskRequest(value=10.0)


def test_accept_task_requires_task_id_and_twin():
    with pytest.raises(ValidationError):
        AcceptTaskRequest(twin_id="twin-1")


def test_complete_task_requires_task_id():
    with pytest.raises(ValidationError):
        CompleteTaskRequest()


def test_marketplace_task_model():
    t = MarketplaceTask(id=1, title="x", value=1.0, status="open")
    assert t.id == 1
