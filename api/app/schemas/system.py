from typing import Optional, List
from pydantic import BaseModel


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    sensor_mode: str
    connections_total: int
    alerts_total: int


class FetchAnalyzeResponse(BaseModel):
    status: str
    message: str
    new_connections_ingested: int
    new_alerts_detected: int
    alerts_summary: dict


class SensorResetResponse(BaseModel):
    status: str
    message: str
