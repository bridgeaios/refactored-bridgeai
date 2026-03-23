"""
Unit tests for economy domain service facade.
Uses mocked memory so no Redis needed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domains.economy.services import EconomyServices
from app.core.errors import NotFoundError, ValidationError


@pytest.fixture
def mock_mem():
    m = MagicMock()
    m.get = AsyncMock(return_value=None)
    m.set = AsyncMock(return_value=True)
    m.append = AsyncMock(return_value=True)
    m.get_recent = AsyncMock(return_value=[])
    return m


@pytest.fixture
def eco(mock_mem):
    return EconomyServices(memory=mock_mem)


@pytest.mark.asyncio
async def test_collect_revenue(eco):
    result = await eco.collect(amount=100.0, currency="BRDG", source_project="test")
    assert result["ok"] is True
    # treasury returns { ok, entry: { split: {...} } }
    assert "split" in result.get("entry", result)


@pytest.mark.asyncio
async def test_collect_zero_amount_raises(eco):
    with pytest.raises(ValidationError):
        await eco.collect(amount=0.0)


@pytest.mark.asyncio
async def test_treasury_status(eco):
    result = await eco.treasury_status()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_ubi_can_claim_new_address(eco):
    result = await eco.ubi_can_claim("0xNewAddress")
    assert result is True


def test_post_and_get_task(eco):
    post_result = eco.post_task(title="Build widget", value=50.0, twin_id="twin-1")
    assert post_result["ok"] is True
    task_id = post_result["task_id"]
    tasks = eco.get_tasks()
    ids = [t["id"] for t in tasks]
    assert task_id in ids


def test_accept_nonexistent_task_raises(eco):
    with pytest.raises(NotFoundError):
        eco.accept_task(task_id=99999, twin_id="twin-1")


def test_complete_nonexistent_task_raises(eco):
    with pytest.raises(NotFoundError):
        eco.complete_task(task_id=99999, twin_id="twin-1")
