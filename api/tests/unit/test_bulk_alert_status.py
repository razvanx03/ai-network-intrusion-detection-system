from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from app.schemas.alert import AlertBulkStatusUpdate
from app.services.alert_service import AlertService
from app.repositories.alert_repository import AlertRepository


def test_selected_status_is_committed_once(db):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.update_many_statuses.return_value = [3, 1, 2]
    payload = AlertBulkStatusUpdate(ids=[1, 2, 3], status="RESOLVED")
    assert service.update_many_statuses(payload) == {"updated": 3}
    service.alert_repo.update_many_statuses.assert_called_once_with([1, 2, 3], "RESOLVED")
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_missing_or_archived_selection_rolls_back_every_change(db):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.update_many_statuses.return_value = [1, 2]
    with pytest.raises(LookupError):
        service.update_many_statuses(AlertBulkStatusUpdate(ids=[1, 2, 3], status="RESOLVED"))
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_failed_commit_rolls_back(db):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.update_many_statuses.return_value = [1]
    db.commit.side_effect = RuntimeError("unit commit failure")
    with pytest.raises(RuntimeError):
        service.update_many_statuses(AlertBulkStatusUpdate(ids=[1], status="NEW"))
    db.rollback.assert_called_once()


def test_update_targets_only_selected_active_ai_findings(db):
    db.scalars.return_value.all.return_value = [2, 3]
    assert AlertRepository(db).update_many_statuses([2, 3], "FALSE_POSITIVE") == [2, 3]
    statement = db.scalars.call_args.args[0]
    assert "archive_batch_id IS NULL" in str(statement)
    assert "RETURNING alerts.id" in str(statement)
    assert [2, 3] in statement.compile().params.values()
    assert "analysis" in statement.compile().params.values()
    db.commit.assert_not_called()


@pytest.mark.parametrize("ids,status", [([], "NEW"), ([1, 1], "NEW"), ([0], "NEW"),
    ([-1], "NEW"), ([True], "NEW"), (["1"], "NEW"), (list(range(1, 502)), "NEW"), ([1], "INVALID")])
def test_invalid_selection_is_rejected(ids, status):
    with pytest.raises(ValidationError):
        AlertBulkStatusUpdate(ids=ids, status=status)
