from unittest.mock import MagicMock

import pytest

from app.database import session as module


@pytest.mark.parametrize("exception", [None, RuntimeError("unit handler failed")])
def test_request_database_session_is_closed_even_after_handler_failure(monkeypatch, exception):
    session = MagicMock()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    dependency = module.get_db()
    assert next(dependency) is session
    session.close.assert_not_called()
    if exception:
        with pytest.raises(RuntimeError, match="unit handler failed"):
            dependency.throw(exception)
    else:
        with pytest.raises(StopIteration):
            next(dependency)
    session.close.assert_called_once()
