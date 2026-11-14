import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import httpx
from app.core.config import settings
from app.schemas.sensor import SensorFileIssue
from app.schemas.protocol_event import LogType
from app.integrations.host_probe import probe_host


class SensorBatch(BaseModel):
    batch_id: str = Field(min_length=1)
    records: list[dict[str, Any]]


class SensorFile(BaseModel):
    log_type: LogType = "conn"
    file: str
    file_id: str = Field(min_length=64, max_length=64)
    archived: bool
    first_ts: float


class SensorFileError(ValueError):
    def __init__(self, issue: SensorFileIssue):
        self.issue = issue
        super().__init__(issue.code)


class SensorFileList(BaseModel):
    files: list[SensorFile]
    issues: list[SensorFileIssue] = Field(default_factory=list)


class SensorFileBatch(BaseModel):
    file: str
    file_id: str
    offset: int = Field(ge=0)
    next_offset: int = Field(ge=0)
    has_more: bool
    records_returned: int = Field(ge=0)
    records: list[dict[str, Any]]

logger = logging.getLogger("nids.sensor_client")


class SensorResetError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class SensorClient:
    """
    Client for interacting with the Zeek sensor agent.
    Supports:
    - Real Remote VM HTTP mode (via httpx)
    - Simulated local mock mode using pre-recorded realistic Zeek samples
    """

    def __init__(self):
        self.mock_mode = settings.SENSOR_MOCK_MODE
        self.base_url = settings.SENSOR_AGENT_URL.rstrip("/")
        self.api_key = settings.SENSOR_AGENT_API_KEY
        self.samples_dir = Path(__file__).resolve().parent.parent.parent / "data" / "samples"
        self._mock_step = 0

    async def fetch_new_logs(self) -> SensorBatch:
        """Fetch unread Zeek conn.log items from remote agent or mock generator."""
        if self.mock_mode:
            return SensorBatch(batch_id=f"mock-{self._mock_step}", records=self._fetch_mock_logs())
        
        raise RuntimeError("Remote sensors require file discovery and backend-owned cursors.")

    async def list_files(self) -> list[SensorFile]:
        return (await self.discover_files()).files

    async def health(self):
        async with httpx.AsyncClient(timeout=5.0) as client:
            return await client.get(f"{self.base_url}/health", headers={"X-API-Key": self.api_key})

    async def require_reset_support(self):
        if self.mock_mode:
            raise SensorResetError("reset_not_supported")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/reset/capabilities", headers={"X-API-Key": self.api_key})
                if response.status_code == 404:
                    raise SensorResetError("reset_not_supported")
                response.raise_for_status()
                if response.json().get("supported") is not True:
                    raise SensorResetError("reset_not_supported")
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise SensorResetError("reset_sensor_failed") from exc

    async def reset_logs(self, operation_id):
        try:
            async with httpx.AsyncClient(timeout=310.0) as client:
                response = await client.post(f"{self.base_url}/reset", headers={"X-API-Key": self.api_key},
                                             json={"operation_id": operation_id, "confirmation": "RESET"})
                response.raise_for_status()
                body = response.json()
                if body.get("operation_id") != operation_id or body.get("status") != "completed":
                    raise SensorResetError("reset_sensor_failed")
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise SensorResetError("reset_sensor_failed") from exc

    async def host_status(self):
        return await probe_host(self.base_url)

    async def discover_files(self) -> SensorFileList:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/files", headers={"X-API-Key": self.api_key})
            response.raise_for_status()
            return SensorFileList.model_validate(response.json())

    async def read_file(self, file: SensorFile, offset: int) -> SensorFileBatch:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/logs", headers={"X-API-Key": self.api_key},
                params={"file": file.file, "file_id": file.file_id, "offset": offset, "limit": 500},
            )
            if response.status_code == 422:
                body = response.json()
                detail = body.get("detail") if isinstance(body, dict) else None
                if isinstance(detail, dict) and detail.get("code") in (
                    "corrupt_file", "unreadable_file", "oversized_file",
                ):
                    raise SensorFileError(SensorFileIssue(
                        file=file.file, code=detail["code"], offset=offset,
                    ))
            response.raise_for_status()
            batch = SensorFileBatch.model_validate(response.json())
        if (batch.file_id != file.file_id or batch.file != file.file or batch.offset != offset
                or batch.next_offset < offset or batch.records_returned != len(batch.records)
                or ((batch.has_more or batch.records) and batch.next_offset <= offset)):
            raise RuntimeError("Sensor returned an inconsistent file cursor.")
        return batch

    async def acknowledge(self, batch_id: str) -> None:
        """Advance the local mock generator after a successful transaction."""
        if self.mock_mode:
            if batch_id == f"mock-{self._mock_step}":
                self._mock_step += 1
            return
        raise RuntimeError("Remote file cursors are committed in the backend database.")


    def _fetch_mock_logs(self) -> List[Dict[str, Any]]:
        """Simulate incremental batches of Zeek logs (normal -> portscan -> bruteforce)."""
        sample_files = [
            "zeek_sample_batch1.json",
            "zeek_sample_batch2.json",
            "zeek_sample_batch3.json",
        ]
        
        target_file = self.samples_dir / sample_files[self._mock_step % len(sample_files)]

        if not target_file.exists():
            raise FileNotFoundError(
                f"Critical mock sample file missing: {target_file}. Sensor mock mode cannot proceed without sample data."
            )

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
                logger.info(f"Loaded {len(logs)} mock Zeek logs from {target_file.name}")
                return logs
        except Exception as e:
            raise ValueError(f"Corrupt or invalid JSON in mock file {target_file}: {e}")


sensor_client = SensorClient()
