import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.schemas.sensor import SensorFileIssue
from app.repositories.sensor_file_problem_repository import SensorFileProblemRepository
from app.services.sensor_file_problem_service import SensorFileProblemService, ProblemNotFoundError, ProblemNotBlockedError
from app.services.analysis_service import AnalysisBusyError
from app.services.ingestion_service import IngestionService
from app.integrations.sensor_client import SensorFile, SensorFileList, SensorFileBatch


def issue(**changes):
    return SensorFileIssue(**{"file":"day/conn.log.gz", "code":"corrupt_file", "offset":333,
                             "archived":True, "fingerprint":"a"*64, **changes})


def test_first_permanent_error_is_recorded_once_without_advancing_or_completing_cursor(db):
    repo = SensorFileProblemRepository(db)
    assert repo.record("sensor", issue(), "first") is True
    problem = db.add.call_args.args[0]
    assert (problem.status, problem.attempts, problem.first_session_id) == ("blocked",1,"first")
    db.scalar.return_value = problem
    assert repo.record("sensor", issue(), "later") is False
    assert (problem.attempts, problem.last_session_id) == (1,"first")
    assert all("sensor_cursors" not in str(call.args[0]) for call in db.execute.call_args_list)


@pytest.mark.parametrize("archived,code", [(False,"corrupt_file"),(True,"unreadable_file"),(True,"file_unavailable")])
def test_current_files_and_temporary_failures_are_never_quarantined(db, archived, code):
    assert SensorFileProblemRepository(db).record("sensor", SensorFileIssue(file="conn.log",archived=archived,
        code=code,fingerprint="a"*64),"session") is True
    db.add.assert_not_called()
    db.execute.assert_not_called()


def test_explicit_retry_failure_updates_existing_history_instead_of_creating_duplicates(db):
    problem = SimpleNamespace(status="retry", attempts=1, first_session_id="original")
    db.scalar.return_value = problem
    assert SensorFileProblemRepository(db).record("sensor",issue(),"retry-session") is True
    assert problem.status == "blocked" and problem.attempts == 2
    assert problem.first_session_id == "original" and problem.last_session_id == "retry-session"
    db.add.assert_not_called()


def test_history_and_exclusions_are_scoped_to_the_configured_sensor(db):
    repo = SensorFileProblemRepository(db)
    db.scalars.return_value.all.return_value = []
    repo.excluded_versions("sensor-A")
    statement = db.scalars.call_args.args[0]
    assert "sensor-A" in statement.compile().params.values() and "blocked" in statement.compile().params.values()
    db.scalar.return_value = 0
    repo.page("sensor-A",20,40)
    assert str(db.scalar.call_args.args[0].whereclause) == str(db.scalars.call_args.args[0].whereclause)


def test_repair_or_manual_retry_replays_safely_against_original_checkpoint(db, monkeypatch, raw_record):
    service = IngestionService(db)
    service.cursors = MagicMock()
    service.cursors.get.return_value = SimpleNamespace(offset=333,completed=False)
    service.problems = MagicMock()
    service.problems.excluded_versions.return_value = []
    service.problems.replay_needed.return_value = True
    service.connections = MagicMock()
    file = SensorFile(file="conn.log.gz",file_id="b"*64,fingerprint="c"*64,archived=True,first_ts=1)
    sensor = SimpleNamespace(mock_mode=False,base_url="sensor",discover_files=AsyncMock(return_value=SensorFileList(files=[file])),
        read_file=AsyncMock(return_value=SensorFileBatch(file=file.file,file_id=file.file_id,offset=0,next_offset=333,
            has_more=False,records_returned=1,records=[raw_record])))
    monkeypatch.setattr("app.services.ingestion_service.sensor_client", sensor)
    async def consume():
        async for batch in service.batches(): service.persist(batch)
    asyncio.run(consume())
    sensor.read_file.assert_awaited_once_with(file,0)
    service.cursors.advance.assert_called_once_with("sensor",file.file_id,file.file,333,333,True)
    service.problems.resolve.assert_called_once_with("sensor",file.file)
    db.commit.assert_not_called()  # Completion is committed together with successful import by the caller.


def test_retry_only_queues_known_blocked_problem_and_is_rolled_back_while_analysis_runs(db, monkeypatch):
    service = SensorFileProblemService(db)
    service.problems = MagicMock()
    problem = SimpleNamespace(status="blocked")
    service.problems.lock.return_value = problem
    assert service.retry("id") == {"status":"retry"}
    assert problem.status == "retry"
    db.commit.assert_called_once()
    service.problems.lock.return_value = None
    with pytest.raises(ProblemNotFoundError):service.retry("missing")
    service.problems.lock.return_value = SimpleNamespace(status="resolved")
    with pytest.raises(ProblemNotBlockedError):service.retry("resolved")
    monkeypatch.setattr("app.services.sensor_file_problem_service.AnalysisRepository", lambda _: SimpleNamespace(running=lambda:object()))
    with pytest.raises(AnalysisBusyError):service.retry("busy")
