"""Unit dependencies only: never import the real .env, open SQL or contact a VM."""
from datetime import datetime, timezone
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Substitute the configuration dependency before importing application modules.
# This deliberately does not exercise startup/config loading; production still
# requires its .env. The unit suite also works in a fresh checkout without one.
if "app.core.config" in sys.modules:
    raise RuntimeError("Unit isolation requires configuration not to be imported beforehand.")
unit_settings = SimpleNamespace(
    PROJECT_NAME="AI NIDS unit suite", ENVIRONMENT="unit", DEBUG=False,
    API_PREFIX="/api", SECRET_KEY="unit-only-signing-key-not-for-deployment-123456789",
    ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=30,
    COOKIE_SECURE=True, COOKIE_SAMESITE="strict",
    ADMIN_USERNAME="unit-admin", ADMIN_PASSWORD="unit-only-password",
    DATABASE_URL="sqlite://", CORS_ORIGINS=["https://unit.invalid"],
    SENSOR_MOCK_MODE=False, SENSOR_AGENT_URL="https://sensor.invalid",
    SENSOR_AGENT_API_KEY="unit-only-sensor-key",
)
config_dependency = ModuleType("app.core.config")
config_dependency.settings = unit_settings
sys.modules["app.core.config"] = config_dependency


@pytest.fixture(autouse=True)
def forbid_external_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests must not connect to a database or network.")

    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request",
                        AsyncMock(side_effect=forbidden))


@pytest.fixture
def db():
    session = MagicMock(spec=Session)
    session.scalar.return_value = None
    return session


@pytest.fixture
def raw_record():
    return {
        "uid": "Cunit01", "ts": 1700000000.5,
        "id.orig_h": "192.0.2.10", "id.orig_p": 51000,
        "id.resp_h": "198.51.100.20", "id.resp_p": 443,
        "proto": "tcp", "service": "ssl", "duration": 2.5,
        "orig_bytes": 100, "resp_bytes": 400, "orig_pkts": 3,
        "resp_pkts": 4, "conn_state": "SF", "history": "ShADadFf",
    }


@pytest.fixture
def connection_factory(raw_record):
    from app.models.connection import Connection
    from app.schemas.connection import ZeekLogItem

    def make(connection_id=1, **overrides):
        values = ZeekLogItem.model_validate(raw_record).model_dump()
        values.update(uid=f"Cunit{connection_id}")
        values.update(overrides)
        return Connection(id=connection_id, **values)

    return make


@pytest.fixture
def admin():
    from app.models.user import User

    return User(id=7, username="unit-admin", hashed_password="unit-placeholder",
                is_active=True, is_admin=True, created_at=datetime.now(timezone.utc))


@pytest.fixture
def mock_http(monkeypatch):
    """Run real httpx request/response validation with in-process transport only."""
    client_type = httpx.AsyncClient
    requests = []

    def install(handler):
        def dispatch(request):
            requests.append(request)
            return handler(request)

        transport = httpx.MockTransport(dispatch)
        monkeypatch.setattr(httpx, "AsyncClient",
                            lambda **kwargs: client_type(transport=transport, **kwargs))
        return requests

    return install
