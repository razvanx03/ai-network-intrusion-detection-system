from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from unittest.mock import MagicMock

from fastapi import HTTPException, Response
import jwt
import pytest
from starlette.requests import Request

from app.core.config import settings
from app.core.constants import COOKIE_ACCESS_TOKEN_KEY
from app.core import security
from app.routes import auth_routes, deps
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.services import auth_service


@pytest.fixture(scope="module")
def password_hash():
    return security.hash_password("unit-password-123")


@pytest.fixture(autouse=True)
def no_revocations(monkeypatch):
    repository = MagicMock()
    repository.is_revoked.return_value = False
    monkeypatch.setattr(deps, "TokenRepository", lambda db: repository)


def test_password_roundtrip_and_wrong_password(password_hash):
    assert password_hash != "unit-password-123"
    assert security.verify_password("unit-password-123", password_hash)
    assert not security.verify_password("wrong-password", password_hash)


@pytest.mark.parametrize("encoded", ["", "plain-text", "$2b$broken"])
def test_malformed_password_hash_is_rejected(encoded):
    assert security.verify_password("password", encoded) is False


def test_token_roundtrip_has_subject_and_configured_expiration():
    before = datetime.now(timezone.utc).timestamp()
    payload = security.decode_access_token(security.create_access_token(7))
    assert payload["sub"] == "7"
    assert before - 1 <= payload["iat"] <= before + 2
    assert payload["exp"] - payload["iat"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_expired_token_is_rejected():
    token = security.create_access_token("unit-admin", timedelta(seconds=-10))
    assert security.decode_access_token(token) is None


@pytest.mark.parametrize("key,algorithm", [("incorrect-key" * 4, "HS256"),
                                         (settings.SECRET_KEY, "HS384")])
def test_wrong_signature_or_algorithm_is_rejected(key, algorithm):
    token = jwt.encode({"sub": "unit-admin"}, key, algorithm=algorithm)
    assert security.decode_access_token(token) is None


def test_malformed_token_is_rejected():
    assert security.decode_access_token("not.a.valid-token") is None


def request_with_token(token=None, bearer=None):
    headers = []
    if token is not None:
        headers.append((b"cookie", f"{COOKIE_ACCESS_TOKEN_KEY}={token}".encode()))
    if bearer is not None:
        headers.append((b"authorization", f"Bearer {bearer}".encode()))
    return Request({"type": "http", "headers": headers})


def test_bearer_header_cannot_replace_cookie(db, monkeypatch):
    repository = MagicMock()
    monkeypatch.setattr(deps, "UserRepository", repository)
    with pytest.raises(HTTPException) as error:
        deps.get_current_user(request_with_token(bearer=security.create_access_token("unit-admin")), db)
    assert error.value.status_code == 401
    repository.assert_not_called()


@pytest.mark.parametrize("payload", [None, {}, {"exp": 1}])
def test_invalid_cookie_does_not_query_users(payload, db, monkeypatch):
    repository = MagicMock()
    monkeypatch.setattr(deps, "UserRepository", repository)
    monkeypatch.setattr(deps, "decode_access_token", lambda token: payload)
    with pytest.raises(HTTPException) as error:
        deps.get_current_user(request_with_token("invalid"), db)
    assert error.value.status_code == 401
    repository.assert_not_called()


@pytest.mark.parametrize("active,is_admin,expected", [(True, True, None),
    (False, True, 403), (True, False, 403), (False, False, 403)])
def test_cookie_requires_active_administrator(active, is_admin, expected, admin, db, monkeypatch):
    admin.is_active, admin.is_admin = active, is_admin
    repository = MagicMock()
    repository.get_by_username.return_value = admin
    monkeypatch.setattr(deps, "UserRepository", lambda db: repository)
    request = request_with_token(security.create_access_token(admin.username))
    if expected:
        with pytest.raises(HTTPException) as error:
            deps.get_current_user(request, db)
        assert error.value.status_code == expected
    else:
        assert deps.get_current_user(request, db) is admin
    repository.get_by_username.assert_called_once_with(admin.username)


def test_deleted_user_session_is_rejected(db, monkeypatch):
    repository = MagicMock()
    repository.get_by_username.return_value = None
    monkeypatch.setattr(deps, "UserRepository", lambda db: repository)
    with pytest.raises(HTTPException) as error:
        deps.get_current_user(request_with_token(security.create_access_token("deleted")), db)
    assert error.value.status_code == 401


@pytest.mark.parametrize("user_state", ["missing", "inactive", "non_admin"])
def test_authentication_rejects_ineligible_users_before_password_check(user_state, admin, db, monkeypatch):
    service = auth_service.AuthService(db)
    service.user_repo = MagicMock()
    admin.is_active = user_state != "inactive"
    admin.is_admin = user_state != "non_admin"
    service.user_repo.get_by_username.return_value = None if user_state == "missing" else admin
    verify = MagicMock()
    monkeypatch.setattr(auth_service, "verify_password", verify)
    assert service.authenticate_user(LoginRequest(username=admin.username, password="wrong")) is None
    verify.assert_not_called()


@pytest.mark.parametrize("valid", [True, False])
def test_authentication_only_issues_token_after_password_verification(valid, admin, db, monkeypatch):
    service = auth_service.AuthService(db)
    service.user_repo = MagicMock()
    service.user_repo.get_by_username.return_value = admin
    monkeypatch.setattr(auth_service, "verify_password", lambda *args: valid)
    issue_token = MagicMock(return_value="unit-token")
    monkeypatch.setattr(auth_service, "create_access_token", issue_token)
    result = service.authenticate_user(LoginRequest(username=admin.username, password="unit-password"))
    if valid:
        assert result.access_token == "unit-token"
        assert result.user.username == admin.username
        assert "hashed_password" not in result.user.model_dump()
        issue_token.assert_called_once_with(subject=admin.username)
    else:
        assert result is None
        issue_token.assert_not_called()


def test_login_keeps_token_only_in_secure_httponly_cookie(admin, db, monkeypatch):
    token = TokenResponse(access_token="unit-token", expires_in_minutes=30,
                          user=UserResponse.model_validate(admin))
    service = MagicMock()
    service.authenticate_user.return_value = token
    monkeypatch.setattr(auth_routes, "AuthService", lambda db: service)
    response = Response()
    result = auth_routes.login(LoginRequest(username=admin.username, password="unit-password"), response, db)
    cookie = SimpleCookie(response.headers["set-cookie"])[COOKIE_ACCESS_TOKEN_KEY]
    assert cookie.value == "unit-token"
    assert cookie["httponly"] and cookie["secure"]
    assert cookie["samesite"] == "strict" and cookie["path"] == "/"
    assert int(cookie["max-age"]) == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert "access_token" not in result.model_dump()
    assert result.user.id == admin.id


def test_failed_login_does_not_set_cookie(db, monkeypatch):
    service = MagicMock()
    service.authenticate_user.return_value = None
    monkeypatch.setattr(auth_routes, "AuthService", lambda db: service)
    response = Response()
    with pytest.raises(HTTPException) as error:
        auth_routes.login(LoginRequest(username="unknown", password="wrong"), response, db)
    assert error.value.status_code == 401
    assert "set-cookie" not in response.headers


def test_logout_expires_same_cookie(db):
    response = Response()
    assert auth_routes.logout(request_with_token(), response, db)["status"] == "success"
    cookie = SimpleCookie(response.headers["set-cookie"])[COOKIE_ACCESS_TOKEN_KEY]
    assert cookie["max-age"] == "0" and cookie["path"] == "/"
    assert cookie["secure"] and cookie["httponly"] and cookie["samesite"] == "strict"
