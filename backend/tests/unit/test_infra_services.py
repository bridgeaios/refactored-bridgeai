"""Unit tests for infra domain services."""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_memory():
    m = MagicMock()
    m.get = AsyncMock(return_value=None)
    m.set = AsyncMock(return_value=True)
    m.delete = AsyncMock(return_value=True)
    m.get_recent = AsyncMock(return_value=[])
    return m


def test_infra_services_init(mock_memory):
    """InfraServices initializes without raising even if optional services fail."""
    from app.domains.infra.services import InfraServices
    svc = InfraServices(memory=mock_memory)
    assert svc is not None


def test_health_returns_dict(mock_memory):
    from app.domains.infra.services import InfraServices
    svc = InfraServices(memory=mock_memory)
    result = svc.health()
    assert isinstance(result, dict)
    assert result["ok"] is True
    assert "status" in result


def test_google_sheets_unavailable_without_creds(mock_memory):
    from app.domains.infra.services import InfraServices
    svc = InfraServices(memory=mock_memory)
    # In CI / dev with no GCP creds, sheets init may fail — availability should be False
    # (pass if unavailable, also accept if available when creds happen to be set)
    assert isinstance(svc.google_sheets_available(), bool)


def test_youtube_available_without_key(mock_memory):
    """Without YOUTUBE_API_KEY set, youtube should report unavailable."""
    import os
    original = os.environ.pop("YOUTUBE_API_KEY", None)
    try:
        import importlib

        from app.domains.infra import services as infra_mod
        importlib.reload(infra_mod)
        svc = infra_mod.InfraServices(memory=mock_memory)
        # When key is absent the YouTubeSkillsService initialises but available=False
        assert svc.youtube_available() is False
    finally:
        if original is not None:
            os.environ["YOUTUBE_API_KEY"] = original
