from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.routing import APIRoute
import pytest

from app.routes import alert_routes, analysis_routes, connection_routes, system_routes
from app.routes.deps import get_current_user
from app.services.analysis_service import AnalysisRunError


@pytest.mark.parametrize("code,status", [("invalid_records", 422), ("sensor_unavailable", 502),
    ("cursor_conflict", 409), ("detector_failed", 500), ("processing_failed", 500)])
def test_analysis_error_response_has_safe_code_and_session_reference(code, status):
    error = analysis_routes.run_error(AnalysisRunError("unit-session", code))
    assert error.status_code == status
    assert error.detail == {"code": code, "analysis_session_id": "unit-session"}


def test_missing_analysis_session_is_404_instead_of_empty_results():
    repository = MagicMock()
    repository.get.return_value = None
    with pytest.raises(HTTPException) as error:
        analysis_routes.require_session(repository, "missing-session")
    assert error.value.status_code == 404


def contains_admin_dependency(dependant):
    return dependant.call is get_current_user or any(
        contains_admin_dependency(child) for child in dependant.dependencies)


@pytest.mark.parametrize("router", [alert_routes.router, analysis_routes.router,
                                    connection_routes.router, system_routes.router],
                         ids=["alerts", "analysis", "connections", "system"])
def test_every_data_and_system_route_declares_admin_authentication(router):
    # Inspect FastAPI's resolved dependency graph without starting the API.
    routes = [route for route in router.routes if isinstance(route, APIRoute)]
    assert routes
    for route in routes:
        assert contains_admin_dependency(route.dependant), f"Unprotected route: {route.path}"
