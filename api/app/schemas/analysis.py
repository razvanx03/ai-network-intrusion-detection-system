from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.sensor import SensorFileIssue


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["sensor"] = "sensor"


class AnalysisSessionResponse(BaseModel):
    archive_batch_id: str | None = None
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: str
    status: Literal["running", "completed", "failed", "interrupted"]
    detector_status: Literal["not_configured", "configured"]
    detector_name: str
    detector_version: str | None
    preparation_version: str
    records_received: int
    new_connections_ingested: int
    records_prepared: int
    new_alerts_detected: int
    error_code: str | None
    file_issues: list[SensorFileIssue] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None

    @field_validator("started_at", "finished_at")
    @classmethod
    def utc_dates(cls, value):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value
