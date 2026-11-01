from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException, Response
import jwt
import pytest
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from app.core.config import settings
from app.core.constants import COOKIE_ACCESS_TOKEN_KEY
from app.core.security import create_access_token, decode_access_token, token_fingerprint
from app.repositories.token_repository import TokenRepository
from app.routes import auth_routes, deps
from app.services import auth_service


def request(token=None):
    return Request({"type": "http", "headers": [] if token is None else [
        (b"cookie", f"{COOKIE_ACCESS_TOKEN_KEY}={token}".encode())]})


@pytest.mark.parametrize("legacy", [False, True])
def test_logout_rejects_copied_token_and_signature_aliases_but_preserves_other_session(legacy, admin, db, monkeypatch):
    revoked = set()
    repository = SimpleNamespace(is_revoked=lambda value: value in revoked,
                                revoke=lambda value, expires: revoked.add(value))
    monkeypatch.setattr(auth_service, "TokenRepository", lambda db: repository)
    monkeypatch.setattr(deps, "TokenRepository", lambda db: repository)
    users = MagicMock()
    users.get_by_username.return_value = admin
    monkeypatch.setattr(deps, "UserRepository", lambda db: users)
    token = (jwt.encode({"sub": admin.username, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        settings.SECRET_KEY, algorithm=settings.ALGORITHM) if legacy
             else create_access_token(admin.username))
    other = create_access_token(admin.username)
    assert deps.get_current_user(request(token), db) is admin
    auth_routes.logout(request(token), Response(), db)
    auth_routes.logout(request(token), Response(), db)  # Repeated logout is safe.
    for copied in [token, token + "=", token + "=="]:
        if decode_access_token(copied) is not None:
            assert token_fingerprint(copied) == token_fingerprint(token)
        with pytest.raises(HTTPException) as error:
            deps.get_current_user(request(copied), db)
        assert error.value.status_code == 401
    assert deps.get_current_user(request(other), db) is admin


def test_fresh_logins_issue_distinct_tokens():
    first, second = create_access_token("unit-admin"), create_access_token("unit-admin")
    assert first != second
    assert decode_access_token(first)["jti"] != decode_access_token(second)["jti"]


def test_token_without_expiration_is_not_accepted():
    token = jwt.encode({"sub": "unit-admin"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


@pytest.mark.parametrize("token", [None, "bad-token", create_access_token("unit-admin", timedelta(seconds=-10))])
def test_missing_invalid_or_expired_logout_is_idempotent(token, db, monkeypatch):
    repository = MagicMock()
    monkeypatch.setattr(auth_service, "TokenRepository", repository)
    assert auth_routes.logout(request(token), Response(), db)["status"] == "success"
    repository.assert_not_called()


def test_revocation_failure_does_not_clear_cookie_or_report_success(db, monkeypatch):
    repository = MagicMock()
    repository.revoke.side_effect = RuntimeError("unit database failure")
    monkeypatch.setattr(auth_service, "TokenRepository", lambda db: repository)
    response = Response()
    with pytest.raises(RuntimeError):
        auth_routes.logout(request(create_access_token("unit-admin")), response, db)
    assert "set-cookie" not in response.headers


def test_repository_persists_only_fingerprint_and_new_instance_checks_it(db):
    token = create_access_token("unit-admin")
    fingerprint = token_fingerprint(token)
    stored = {}
    db.get.side_effect = lambda model, key: stored.get(key)
    db.add.side_effect = lambda row: stored.setdefault(row.fingerprint, row)
    TokenRepository(db).revoke(fingerprint, decode_access_token(token)["exp"])
    assert TokenRepository(db).is_revoked(fingerprint)
    assert stored[fingerprint].expires_at == decode_access_token(token)["exp"]
    assert token not in str(vars(stored[fingerprint]))
    db.commit.assert_called_once()


@pytest.mark.parametrize("concurrent", [True, False])
def test_duplicate_logout_race_only_masks_already_persisted_revocation(db, concurrent):
    db.get.side_effect = [None, object() if concurrent else None]
    db.commit.side_effect = IntegrityError("insert", {}, RuntimeError("unit conflict"))
    if concurrent:
        TokenRepository(db).revoke("a" * 64, 9999999999)
    else:
        with pytest.raises(IntegrityError):
            TokenRepository(db).revoke("a" * 64, 9999999999)
    db.rollback.assert_called_once()


def test_storage_failure_rolls_back(db):
    db.get.return_value = None
    db.commit.side_effect = RuntimeError("unit storage failure")
    with pytest.raises(RuntimeError):
        TokenRepository(db).revoke("a" * 64, 9999999999)
    db.rollback.assert_called_once()
