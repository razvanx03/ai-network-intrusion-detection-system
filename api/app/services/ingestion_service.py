"""Existing sensor transport, validation, deduplication and durable file progress."""
from dataclasses import dataclass
from pydantic import ValidationError
from app.integrations.sensor_client import sensor_client, SensorFileError, SensorFileIssue
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.sensor_cursor_repository import SensorCursorRepository
from app.schemas.connection import ZeekLogItem
from app.schemas.protocol_event import LogType, normalize_event
from app.repositories.protocol_event_repository import ProtocolEventRepository
from app.repositories.sensor_file_problem_repository import SensorFileProblemRepository


@dataclass(frozen=True)
class IngestionBatch:
    records: list[dict]
    log_type: LogType = "conn"
    sensor_url: str | None = None
    file_id: str | None = None
    file: str | None = None
    offset: int = 0
    next_offset: int = 0
    completed: bool = False
    issue: SensorFileIssue | None = None
    expected_offset: int | None = None


class IngestionService:
    def __init__(self, db):
        self.db = db
        self.cursors = SensorCursorRepository(db)
        self.connections = ConnectionRepository(db)
        self.problems = SensorFileProblemRepository(db)

    def note_issue(self, issue, session_id):
        return self.problems.record(sensor_client.base_url, issue, session_id)

    async def batches(self):
        if sensor_client.mock_mode:
            batch = await sensor_client.fetch_new_logs()
            yield IngestionBatch(records=batch.records)
            # Caller commits before requesting the next batch.
            await sensor_client.acknowledge(batch.batch_id)
            return
        excluded = self.problems.excluded_versions(sensor_client.base_url)
        self.db.rollback()
        discovery = await sensor_client.discover_files(excluded)
        for empty in discovery.empty_files:
            self.problems.resolve(sensor_client.base_url, empty.file)
        if discovery.empty_files:
            self.db.commit()
        for issue in discovery.issues:
            yield IngestionBatch(records=[], issue=issue)
        for file in discovery.files:
            cursor = self.cursors.get(sensor_client.base_url, file.file_id)
            completed = cursor is not None and cursor.completed
            offset = cursor.offset if cursor is not None else 0
            replay = file.archived and self.problems.replay_needed(sensor_client.base_url, file.file)
            self.db.rollback()
            if completed and not replay:
                continue
            expected = offset
            if replay:
                offset = 0
            while True:
                try:
                    batch = await sensor_client.read_file(file, offset)
                except SensorFileError as exc:
                    yield IngestionBatch(records=[], issue=exc.issue)
                    break
                try:
                    for record in batch.records:
                        if file.log_type == "conn":
                            ZeekLogItem.model_validate(record)
                        else:
                            normalize_event(file.log_type, record)
                except (ValidationError, ValueError):
                    yield IngestionBatch(records=[], issue=SensorFileIssue(
                        file=file.file, code="corrupt_file", offset=offset,
                        archived=file.archived, fingerprint=file.fingerprint,
                    ))
                    break
                yield IngestionBatch(
                    records=batch.records, log_type=file.log_type, sensor_url=sensor_client.base_url,
                    file_id=file.file_id, file=file.file, offset=offset,
                    next_offset=batch.next_offset, completed=file.archived and not batch.has_more,
                    expected_offset=expected if replay else None,
                )
                expected = batch.next_offset
                offset = batch.next_offset
                if not batch.has_more:
                    break

    def persist(self, batch: IngestionBatch):
        validated = [ZeekLogItem.model_validate(record).model_dump() if batch.log_type == "conn"
                     else normalize_event(batch.log_type, record) for record in batch.records]
        if batch.file_id is not None:
            self.cursors.advance(batch.sensor_url, batch.file_id, batch.file,
                                 batch.expected_offset if batch.expected_offset is not None else batch.offset,
                                 batch.next_offset, batch.completed)
        if batch.completed:
            self.problems.resolve(batch.sensor_url, batch.file)
        if batch.log_type != "conn":
            ProtocolEventRepository(self.db).create_batch(validated)
            return []
        return self.connections.create_batch(validated)
