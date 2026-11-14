import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError
import pytest

from app.integrations.sensor_client import SensorBatch, SensorFile, SensorFileBatch, SensorFileList, SensorFileError
from app.schemas.sensor import SensorFileIssue
from app.repositories.sensor_cursor_repository import CursorConflictError, SensorCursorRepository
from app.services import ingestion_service as module
from app.services.ingestion_service import IngestionBatch, IngestionService


@pytest.fixture
def ingestion(db, monkeypatch):
    service = IngestionService(db)
    service.cursors = MagicMock()
    service.connections = MagicMock()
    sensor = SimpleNamespace(mock_mode=False, base_url="https://sensor.invalid",
        discover_files=AsyncMock(return_value=SensorFileList(files=[])), read_file=AsyncMock(),
        fetch_new_logs=AsyncMock(), acknowledge=AsyncMock())
    monkeypatch.setattr(module, "sensor_client", sensor)
    return service, sensor


def test_repaired_empty_archive_resolves_history_without_advancing_a_cursor(ingestion):
    service, sensor = ingestion
    service.problems = MagicMock()
    service.problems.excluded_versions.return_value = ["a" * 64]
    sensor.discover_files.return_value = SensorFileList(files=[], empty_files=[
        {"file": "day/conn.log.gz", "fingerprint": "b" * 64}])

    async def collect():
        return [batch async for batch in service.batches()]

    assert asyncio.run(collect()) == []
    sensor.discover_files.assert_awaited_once_with(["a" * 64])
    service.problems.resolve.assert_called_once_with(sensor.base_url, "day/conn.log.gz")
    service.db.commit.assert_called_once()
    service.cursors.advance.assert_not_called()
    sensor.read_file.assert_not_awaited()


def test_discovery_failure_does_not_resolve_history_or_advance_progress(ingestion):
    service, sensor = ingestion
    service.problems = MagicMock()
    sensor.discover_files.side_effect = RuntimeError("unit manifest failure")

    async def collect():
        return [batch async for batch in service.batches()]

    with pytest.raises(RuntimeError, match="manifest failure"):
        asyncio.run(collect())
    service.problems.resolve.assert_not_called()
    service.cursors.advance.assert_not_called()
    service.db.commit.assert_not_called()


def test_completed_archive_manual_retry_replays_multiple_pages_with_compare_and_swap(ingestion, raw_record):
    service, sensor = ingestion
    service.problems = MagicMock()
    service.problems.replay_needed.return_value = True
    service.problems.excluded_versions.return_value = []
    service.cursors.get.return_value = SimpleNamespace(offset=300, completed=True)
    file = SensorFile(file="day/conn.log.gz", file_id="a" * 64, archived=True,
                      first_ts=1, fingerprint="b" * 64)
    sensor.discover_files.return_value = SensorFileList(files=[file])

    def read(source, offset):
        return SensorFileBatch(file=source.file, file_id=source.file_id, offset=offset,
            next_offset=offset + 100, records=[raw_record], records_returned=1, has_more=offset == 0)

    sensor.read_file.side_effect = read

    async def consume():
        async for batch in service.batches():
            service.persist(batch)

    asyncio.run(consume())
    assert [call.args for call in sensor.read_file.await_args_list] == [(file, 0), (file, 100)]
    assert [call.args for call in service.cursors.advance.call_args_list] == [
        (sensor.base_url, file.file_id, file.file, 300, 100, False),
        (sensor.base_url, file.file_id, file.file, 100, 200, True)]
    service.problems.resolve.assert_called_once_with(sensor.base_url, file.file)
    service.db.commit.assert_not_called()  # The analysis owns the batch transactions.


@pytest.mark.parametrize("log_type", ["dns", "http", "ssl"])
def test_invalid_context_batch_is_reported_with_version_without_persisting_partial_records(ingestion, log_type):
    service, sensor = ingestion
    service.problems = MagicMock()
    service.problems.replay_needed.return_value = False
    service.cursors.get.return_value = None
    file = SensorFile(file=f"day/{log_type}.log.gz", file_id="a" * 64, archived=True,
                      log_type=log_type, first_ts=1, fingerprint="b" * 64)
    sensor.discover_files.return_value = SensorFileList(files=[file])
    sensor.read_file.return_value = SensorFileBatch(file=file.file, file_id=file.file_id,
        offset=0, next_offset=100, records_returned=2, has_more=False,
        records=[{"uid": "Cvalid", "ts": 1}, {"ts": 2}])

    async def collect():
        return [batch async for batch in service.batches()]

    batches = asyncio.run(collect())
    assert len(batches) == 1 and batches[0].records == []
    assert batches[0].issue == SensorFileIssue(file=file.file, code="corrupt_file",
        offset=0, archived=True, fingerprint=file.fingerprint)
    service.cursors.advance.assert_not_called()
    service.problems.resolve.assert_not_called()
    service.connections.create_batch.assert_not_called()


def test_validation_precedes_cursor_advance_or_inserts(ingestion, raw_record):
    service, _ = ingestion
    batch = IngestionBatch(records=[raw_record, {**raw_record, "duration": -1}],
                           sensor_url="unit", file_id="a" * 64, file="conn.log")
    with pytest.raises(ValidationError):
        service.persist(batch)
    service.cursors.advance.assert_not_called()
    service.connections.create_batch.assert_not_called()


def test_persist_normalizes_records_and_updates_durable_progress(ingestion, raw_record):
    service, _ = ingestion
    batch = IngestionBatch(records=[{**raw_record, "duration": "-"}],
        sensor_url="unit", file_id="a" * 64, file="conn.log", offset=10, next_offset=200, completed=True)
    assert service.persist(batch) is service.connections.create_batch.return_value
    service.cursors.advance.assert_called_once_with("unit", "a" * 64, "conn.log", 10, 200, True)
    normalized = service.connections.create_batch.call_args.args[0][0]
    assert normalized["duration"] is None and normalized["src_ip"] == "192.0.2.10"
    assert "id.orig_h" not in normalized


def test_cursor_conflict_prevents_connection_insert(ingestion, raw_record):
    service, _ = ingestion
    service.cursors.advance.side_effect = CursorConflictError("unit race")
    with pytest.raises(CursorConflictError):
        service.persist(IngestionBatch(records=[raw_record], file_id="a" * 64))
    service.connections.create_batch.assert_not_called()


def test_archives_skip_completed_and_resume_partial_before_current_file(ingestion, raw_record):
    service, sensor = ingestion
    files = [SensorFile(file=name, file_id=str(index) * 64, archived=index != 3, first_ts=index, fingerprint="f" * 64)
             for index, name in enumerate(["done.gz", "partial.gz", "current/conn.log"], 1)]
    sensor.discover_files.return_value = SensorFileList(files=files)
    service.cursors.get.side_effect = [SimpleNamespace(completed=True, offset=900),
                                       SimpleNamespace(completed=False, offset=100), None]

    def read(file, offset):
        has_more = file == files[1] and offset == 100
        return SensorFileBatch(file=file.file, file_id=file.file_id, offset=offset,
            next_offset=offset + 100, has_more=has_more, records_returned=1, records=[raw_record])
    sensor.read_file.side_effect = read

    async def collect():
        return [batch async for batch in service.batches()]
    batches = asyncio.run(collect())
    assert [(batch.file, batch.offset, batch.next_offset, batch.completed) for batch in batches] == [
        ("partial.gz", 100, 200, False), ("partial.gz", 200, 300, True),
        ("current/conn.log", 0, 100, False)]
    assert sensor.read_file.await_count == 3
    assert service.db.rollback.call_count == 4


def test_mock_acknowledgment_waits_until_consumer_resumes(ingestion, raw_record):
    service, sensor = ingestion
    sensor.mock_mode = True
    sensor.fetch_new_logs.return_value = SensorBatch(batch_id="mock-0", records=[raw_record])

    async def scenario():
        stream = service.batches()
        assert (await anext(stream)).records == [raw_record]
        sensor.acknowledge.assert_not_awaited()
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        sensor.acknowledge.assert_awaited_once_with("mock-0")
    asyncio.run(scenario())


@pytest.mark.parametrize("invalid_record", [False, True])
def test_bad_file_is_reported_and_next_file_is_read_without_advancing_bad_cursor(ingestion, raw_record, invalid_record):
    service, sensor = ingestion
    files = [SensorFile(file=name, file_id=str(i) * 64, archived=True, first_ts=i, fingerprint="f" * 64)
             for i, name in enumerate(["broken.log.gz", "healthy.log.gz"], 1)]
    sensor.discover_files.return_value = SensorFileList(files=files,
        issues=[SensorFileIssue(file="bad-header.log.gz", code="corrupt_file")])
    service.cursors.get.return_value = None

    def read(file, offset):
        if file == files[0] and not invalid_record:
            raise SensorFileError(SensorFileIssue(file=file.file, code="corrupt_file", offset=offset))
        records = [{**raw_record, "duration": -1}] if file == files[0] else [raw_record]
        return SensorFileBatch(file=file.file, file_id=file.file_id, offset=offset,
            next_offset=100, has_more=False, records_returned=1, records=records)
    sensor.read_file.side_effect = read

    async def collect():
        return [batch async for batch in service.batches()]
    batches = asyncio.run(collect())
    assert [batch.issue.file for batch in batches if batch.issue] == ["bad-header.log.gz", "broken.log.gz"]
    assert batches[-1].file == "healthy.log.gz" and batches[-1].records == [raw_record]
    service.cursors.advance.assert_not_called()


def test_abandoned_mock_batch_is_not_acknowledged(ingestion):
    service, sensor = ingestion
    sensor.mock_mode = True
    sensor.fetch_new_logs.return_value = SensorBatch(batch_id="mock-0", records=[])

    async def scenario():
        stream = service.batches()
        await anext(stream)
        await stream.aclose()
    asyncio.run(scenario())
    sensor.acknowledge.assert_not_awaited()


def test_new_cursor_must_start_at_zero(db):
    db.get.return_value = None
    repository = SensorCursorRepository(db)
    with pytest.raises(CursorConflictError):
        repository.advance("unit", "a" * 64, "conn.log", 100, 200, False)
    db.add.assert_not_called()


def test_new_cursor_is_flushed_but_not_committed_by_repository(db):
    db.get.return_value = None
    SensorCursorRepository(db).advance("unit", "a" * 64, "archive.gz", 0, 200, True)
    cursor = db.add.call_args.args[0]
    assert (cursor.sensor_url, cursor.file_id, cursor.offset, cursor.completed) == ("unit", "a" * 64, 200, True)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("affected", [0, 2])
def test_cursor_compare_and_swap_requires_exactly_one_updated_row(db, affected):
    db.get.return_value = SimpleNamespace(offset=100)
    db.execute.return_value.rowcount = affected
    with pytest.raises(CursorConflictError):
        SensorCursorRepository(db).advance("unit", "a" * 64, "conn.log", 100, 200, False)


def test_existing_cursor_advance_succeeds_without_committing(db):
    db.get.return_value = SimpleNamespace(offset=100)
    db.execute.return_value.rowcount = 1
    SensorCursorRepository(db).advance("unit", "a" * 64, "conn.log", 100, 200, False)
    db.commit.assert_not_called()
    db.add.assert_not_called()


def test_corrupt_tail_preserves_committed_prefix_and_does_not_complete_file(ingestion, raw_record):
    service, sensor = ingestion
    file = SensorFile(file="partial.log.gz", file_id="a" * 64, archived=True, first_ts=1, fingerprint="f" * 64)
    sensor.discover_files.return_value = SensorFileList(files=[file])
    service.cursors.get.return_value = SimpleNamespace(completed=False, offset=100)
    sensor.read_file.side_effect = [
        SensorFileBatch(file=file.file, file_id=file.file_id, offset=100, next_offset=200,
                        has_more=True, records_returned=1, records=[raw_record]),
        SensorFileError(SensorFileIssue(file=file.file, code="corrupt_file", offset=200)),
    ]

    async def consume():
        batches = []
        async for batch in service.batches():
            batches.append(batch)
            if batch.issue is None:
                service.persist(batch)
                service.db.commit()
        return batches
    batches = asyncio.run(consume())
    service.cursors.advance.assert_called_once_with(sensor.base_url, file.file_id, file.file, 100, 200, False)
    assert batches[1].issue.offset == 200
    assert service.db.commit.call_count == 1
