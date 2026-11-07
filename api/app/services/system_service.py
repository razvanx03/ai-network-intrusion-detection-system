from typing import Any
from app.repositories.overview_repository import OverviewRepository
from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import AnalysisService
from app.integrations.sensor_client import sensor_client
from datetime import datetime, timezone
import httpx


class SystemService:
    def __init__(self, db):
        self.db = db

    def overview(self):
        return OverviewRepository(self.db).summary()

    async def fetch_and_analyze(self, requested_by: int) -> dict[str, Any]:
        return await AnalysisService(self.db).run(requested_by, AnalysisRequest())

    async def sensor_status(self):
        if sensor_client.mock_mode:
            status = "sample_mode"
        else:
            try:
                response = await sensor_client.health()
                if response.status_code in (401, 403):
                    status = "unauthorized"
                elif response.status_code != 200:
                    status = "unavailable"
                else:
                    body = response.json()
                    status = "available" if isinstance(body, dict) and body.get("status") == "ok" and body.get("service") == "zeek-sensor-agent" else "invalid_response"
            except httpx.RequestError:
                host = await sensor_client.host_status()
                status = "unavailable" if host == "reachable" else "host_unreachable" if host == "unreachable" else "host_unknown"
            except ValueError:
                status = "invalid_response"
        return {"status": status, "checked_at": datetime.now(timezone.utc)}
