import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError
import pytest

from app.integrations.sensor_client import SensorBatch, SensorFile, SensorFileBatch
from app.repositories.sensor_cursor_repository import CursorConflictError, SensorCursorRepository
from app.services import ingestion_service as module
from app.services.ingestion_service import IngestionBatch, IngestionService


@pytest.fixture
def ingestion(db, monkeypatch):
    service = IngestionService(db)
    service.cursors = MagicMock()
    service.connections = MagicMock()
    sensor = SimpleNamespace(mock_mode=False, base_url="https://sensor.invalid",
        list_files=AsyncMock(return_value=[]), read_file=AsyncMock(),
        fetch_new_logs=AsyncMock(), acknowledge=AsyncMock())
    monkeypatch.setattr(module, "sensor_client", sensor)
    return service, sensor


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
    files = [SensorFile(file=name, file_id=str(index) * 64, archived=index != 3, first_ts=index)
             for index, name in enumerate(["done.gz", "partial.gz", "current/conn.log"], 1)]
    sensor.list_files.return_value = files
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
    assert service.db.rollback.call_count == 3


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
