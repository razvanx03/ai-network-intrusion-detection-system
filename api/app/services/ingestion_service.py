"""Existing sensor transport, validation, deduplication and durable file progress."""
from dataclasses import dataclass
from pydantic import ValidationError
from app.integrations.sensor_client import sensor_client, SensorFileError, SensorFileIssue
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.sensor_cursor_repository import SensorCursorRepository
from app.schemas.connection import ZeekLogItem


@dataclass(frozen=True)
class IngestionBatch:
    records: list[dict]
    sensor_url: str | None = None
    file_id: str | None = None
    file: str | None = None
    offset: int = 0
    next_offset: int = 0
    completed: bool = False
    issue: SensorFileIssue | None = None


class IngestionService:
    def __init__(self, db):
        self.db = db
        self.cursors = SensorCursorRepository(db)
        self.connections = ConnectionRepository(db)

    async def batches(self):
        if sensor_client.mock_mode:
            batch = await sensor_client.fetch_new_logs()
            yield IngestionBatch(records=batch.records)
            # Caller commits before requesting the next batch.
            await sensor_client.acknowledge(batch.batch_id)
            return
        discovery = await sensor_client.discover_files()
        for issue in discovery.issues:
            yield IngestionBatch(records=[], issue=issue)
        for file in discovery.files:
            cursor = self.cursors.get(sensor_client.base_url, file.file_id)
            completed = cursor is not None and cursor.completed
            offset = cursor.offset if cursor is not None else 0
            self.db.rollback()
            if completed:
                continue
            while True:
                try:
                    batch = await sensor_client.read_file(file, offset)
                except SensorFileError as exc:
                    yield IngestionBatch(records=[], issue=exc.issue)
                    break
                try:
                    for record in batch.records:
                        ZeekLogItem.model_validate(record)
                except ValidationError:
                    yield IngestionBatch(records=[], issue=SensorFileIssue(
                        file=file.file, code="corrupt_file", offset=offset,
                    ))
                    break
                yield IngestionBatch(
                    records=batch.records, sensor_url=sensor_client.base_url,
                    file_id=file.file_id, file=file.file, offset=offset,
                    next_offset=batch.next_offset, completed=file.archived and not batch.has_more,
                )
                offset = batch.next_offset
                if not batch.has_more:
                    break

    def persist(self, batch: IngestionBatch):
        validated = [ZeekLogItem.model_validate(record).model_dump() for record in batch.records]
        if batch.file_id is not None:
            self.cursors.advance(batch.sensor_url, batch.file_id, batch.file,
                                 batch.offset, batch.next_offset, batch.completed)
        return self.connections.create_batch(validated)
