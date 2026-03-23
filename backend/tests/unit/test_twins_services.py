"""Unit tests for twins domain services."""
import pytest
from app.domains.twins.services import TwinsServices


@pytest.fixture
def twins():
    return TwinsServices()


def test_get_profile_default(twins):
    profile = twins.get_profile("default")
    assert profile["twin_id"] == "default"
    assert "status" in profile


@pytest.mark.asyncio
async def test_decide_returns_response(twins):
    result = await twins.decide(prompt="What should I do?", twin_id="default")
    assert "ok" in result


@pytest.mark.asyncio
async def test_emotion_status(twins):
    status = await twins.emotion_status("default")
    assert isinstance(status, dict)
    assert "twin_id" in status


def test_list_bossbots(twins):
    bots = twins.list_bossbots()
    assert isinstance(bots, list)


@pytest.mark.asyncio
async def test_competition_status(twins):
    status = await twins.competition_status()
    assert status["ok"] is True
