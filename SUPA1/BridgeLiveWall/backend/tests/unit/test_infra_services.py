from app.domains.infra.services import InfraServices


def test_infra_services_init(mock_memory):
    svc = InfraServices(memory=mock_memory)
    assert svc is not None
    assert svc._google_sheets is None


def test_health_returns_dict(mock_memory):
    svc = InfraServices(memory=mock_memory)
    result = svc.health()
    assert isinstance(result, dict)
    assert "status" in result
