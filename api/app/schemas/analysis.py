from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.sensor import SensorFileIssue


class AnalysisRequest(BaseModel):
    source: Literal["sensor", "stored"] = "sensor"
    connection_ids: list[int] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_selection(self):
        if self.source == "stored" and not self.connection_ids:
            raise ValueError("Stored analysis requires 1..500 explicit connection IDs.")
        if self.source == "sensor" and self.connection_ids:
            raise ValueError("Connection IDs are only valid for stored analysis.")
        if any(value <= 0 for value in self.connection_ids):
            raise ValueError("Connection IDs must be positive.")
        self.connection_ids = list(dict.fromkeys(self.connection_ids))
        return self


class AnalysisSessionResponse(BaseModel):
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
