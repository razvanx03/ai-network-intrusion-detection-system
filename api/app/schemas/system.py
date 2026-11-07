from pydantic import BaseModel
from app.schemas.analysis import AnalysisSessionResponse


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    sensor_mode: str
    connections_total: int
    alerts_total: int
    legacy_alerts_total: int


class FetchAnalyzeResponse(BaseModel):
    status: str
    message: str
    new_connections_ingested: int
    new_alerts_detected: int
    alerts_summary: dict
    analysis_session: AnalysisSessionResponse


class SensorResetResponse(BaseModel):
    status: str
    message: str


class ProtocolCount(BaseModel):
    proto: str
    count: int


class OverviewResponse(BaseModel):
    connections_total: int
    analyzed_connections: int
    pending_connections: int
    flagged_connections: int
    sessions_total: int
    completed_sessions: int
    failed_sessions: int
    running_session_id: str | None
    protocols: list[ProtocolCount]
