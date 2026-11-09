from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services.archive_service import ArchiveService, EmptyArchiveError, ArchiveNotFoundError
from app.services.analysis_service import AnalysisBusyError
from app.repositories.archive_repository import ArchiveRepository
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.overview_repository import OverviewRepository
from app.routes.analysis_routes import require_session
from app.services.connection_service import ConnectionService


@pytest.fixture
def archives(db):
    service = ArchiveService(db)
    service.archives = MagicMock()
    service.sessions = MagicMock()
    service.sessions.running.return_value = None
    batch = SimpleNamespace(id="a" * 32, connections=4, alerts=2, sessions=1)
    service.archives.create.return_value = batch
    service.archives.restore.return_value = batch
    return service, batch


def test_archive_is_atomic_and_has_no_cursor_dependency(archives):
    service, batch = archives
    assert service.change() is batch
    service.archives.archive.assert_called_once_with(batch)
    service.db.commit.assert_called_once()
    service.db.rollback.assert_not_called()
    assert not hasattr(service, "cursors")


def test_restore_returns_original_lot_without_reimporting_or_reanalyzing(archives):
    service, batch = archives
    assert service.change(batch.id) is batch
    service.archives.restore_records.assert_called_once_with(batch.id)
    service.archives.archive.assert_not_called()
    service.db.commit.assert_called_once()


@pytest.mark.parametrize("batch_id", [None, "a" * 32])
def test_archive_and_restore_refuse_running_analysis_and_release_lock(archives, batch_id):
    service, _ = archives
    service.sessions.running.return_value = object()
    with pytest.raises(AnalysisBusyError):
        service.change(batch_id)
    service.db.commit.assert_not_called()
    service.db.rollback.assert_called_once()
    service.archives.archive.assert_not_called()
    service.archives.restore_records.assert_not_called()


def test_empty_archive_does_not_leave_a_batch(archives):
    service, batch = archives
    batch.connections = batch.alerts = batch.sessions = 0
    with pytest.raises(EmptyArchiveError):
        service.change()
    service.db.rollback.assert_called_once()
    service.db.commit.assert_not_called()


def test_missing_or_restored_batch_cannot_be_restored_again(archives):
    service, _ = archives
    service.archives.restore.return_value = None
    with pytest.raises(ArchiveNotFoundError):
        service.change("missing")
    service.db.rollback.assert_called_once()


@pytest.mark.parametrize("failure", ["archive", "commit"])
def test_write_failures_roll_back_the_whole_lot(archives, failure):
    service, _ = archives
    target = service.archives.archive if failure == "archive" else service.db.commit
    target.side_effect = RuntimeError("unit write failure")
    with pytest.raises(RuntimeError):
        service.change()
    service.db.rollback.assert_called_once()


def test_archive_only_marks_active_rows_and_restore_only_matches_requested_lot(db):
    repo = ArchiveRepository(db)
    repo.archive(SimpleNamespace(id="batch", connections=0, alerts=0, sessions=0))
    statements = [call.args[0] for call in db.execute.call_args_list]
    assert len(statements) == 3
    assert all("archive_batch_id IS NULL" in str(statement) for statement in statements)
    assert all("DELETE" not in str(statement) for statement in statements)
    db.execute.reset_mock()
    repo.restore_records("batch")
    assert all("batch" in call.args[0].compile().params.values() for call in db.execute.call_args_list)


def test_default_lists_hide_archives_but_all_data_can_read_them(db):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    for repo in (ConnectionRepository(db), AlertRepository(db)):
        repo.get_filtered()
        assert "archive_batch_id IS NULL" in str(db.scalars.call_args.args[0])
        repo.get_filtered(include_archived=True)
        assert "archive_batch_id IS NULL" not in str(db.scalars.call_args.args[0])
    AnalysisRepository(db).page(20, 0)
    assert "archive_batch_id IS NULL" in str(db.scalars.call_args.args[0])
    AnalysisRepository(db).page(20, 0, True)
    assert "archive_batch_id IS NULL" not in str(db.scalars.call_args.args[0])


def test_archived_uids_remain_in_deduplication_query(db, raw_record):
    db.scalars.return_value.all.return_value = [raw_record["uid"]]
    assert ConnectionRepository(db).create_batch([raw_record]) == []
    assert "archive_batch_id" not in str(db.scalars.call_args.args[0])
    db.add_all.assert_not_called()


def test_exports_and_stats_only_include_active_alerts(db):
    repo = AlertRepository(db)
    repo.get_all_for_export()
    assert "archive_batch_id IS NULL" in str(db.scalars.call_args.args[0])
    db.scalar.return_value = 0
    db.execute.return_value.all.return_value = []
    repo.get_stats()
    assert all("archive_batch_id IS NULL" in str(call.args[0]) for call in db.execute.call_args_list)
    assert all("archive_batch_id IS NULL" in str(call.args[0]) for call in db.scalar.call_args_list)


def test_overview_hides_archives_in_all_aggregates(db):
    db.scalar.return_value = 0
    db.execute.return_value.all.return_value = []
    OverviewRepository(db).summary()
    for call in db.scalar.call_args_list[:-1]:
        assert "archive_batch_id IS NULL" in str(call.args[0])
    assert all("archive_batch_id IS NULL" in str(call.args[0]) for call in db.execute.call_args_list)


def test_archived_session_and_context_are_only_available_when_requested(db):
    repo = MagicMock()
    repo.get.return_value = SimpleNamespace(archive_batch_id="batch")
    with pytest.raises(HTTPException) as exc:
        require_session(repo, "session")
    assert exc.value.status_code == 404
    assert require_session(repo, "session", True) is repo.get.return_value
    db.get.return_value = SimpleNamespace(uid="Cunit", archive_batch_id="batch")
    with pytest.raises(HTTPException) as exc:
        ConnectionService(db).events(1, "dns", 50, 0)
    assert exc.value.status_code == 404


def test_removed_destructive_and_cursor_routes_do_not_exist():
    from app.routes.system_routes import router
    assert not any(route.path.endswith(("/clear-database", "/reset-sensor")) for route in router.routes)
