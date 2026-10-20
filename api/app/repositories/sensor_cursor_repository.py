from sqlalchemy import delete, update
from sqlalchemy.orm import Session
from app.models.sensor_cursor import SensorCursor


class CursorConflictError(RuntimeError):
    pass


class SensorCursorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, sensor_url: str, file_id: str) -> SensorCursor | None:
        return self.db.get(SensorCursor, (sensor_url, file_id))

    def advance(self, sensor_url: str, file_id: str, file: str,
                expected: int, next_offset: int, completed: bool) -> None:
        cursor = self.get(sensor_url, file_id)
        if cursor is None:
            if expected != 0:
                raise CursorConflictError("Sensor cursor changed; retry the operation.")
            self.db.add(SensorCursor(sensor_url=sensor_url, file_id=file_id,
                                    file=file, offset=next_offset, completed=completed))
            self.db.flush()
            return
        result = self.db.execute(
            update(SensorCursor).where(
                SensorCursor.sensor_url == sensor_url,
                SensorCursor.file_id == file_id,
                SensorCursor.offset == expected,
            ).values(file=file, offset=next_offset, completed=completed)
        )
        if result.rowcount != 1:
            raise CursorConflictError("Sensor cursor changed; retry the operation.")

    def reset(self, sensor_url: str) -> None:
        self.db.execute(delete(SensorCursor).where(SensorCursor.sensor_url == sensor_url))
