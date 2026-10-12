import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger("nids.sensor_client")


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

    async def fetch_new_logs(self) -> List[Dict[str, Any]]:
        """Fetch unread Zeek conn.log items from remote agent or mock generator."""
        if self.mock_mode:
            return self._fetch_mock_logs()
        
        url = f"{self.base_url}/logs"
        headers = {"X-API-Key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch logs from sensor VM ({url}): {e}")
            raise RuntimeError(f"Sensor VM connection failed: {e}")

    async def reset_sensor_logs(self) -> bool:
        """Clear the conn.log file on the remote sensor or reset mock state."""
        if self.mock_mode:
            self._mock_step = 0
            logger.info("Reset mock sensor state to initial step.")
            return True

        url = f"{self.base_url}/logs"
        headers = {"X-API-Key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=headers)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to reset logs on sensor VM ({url}): {e}")
            raise RuntimeError(f"Sensor VM reset failed: {e}")

    def _fetch_mock_logs(self) -> List[Dict[str, Any]]:
        """Simulate incremental batches of Zeek logs (normal -> portscan -> bruteforce)."""
        sample_files = [
            "zeek_sample_batch1.json",
            "zeek_sample_batch2.json",
            "zeek_sample_batch3.json",
        ]
        
        target_file = self.samples_dir / sample_files[self._mock_step % len(sample_files)]
        self._mock_step += 1

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
