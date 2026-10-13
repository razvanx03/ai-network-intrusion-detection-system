import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Header, HTTPException, status
import uvicorn
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
API_KEY = os.getenv("API_KEY", "nids-sensor-agent-secret-key")

# Potential default Zeek log locations
DEFAULT_LOG_PATHS = [
    "/opt/zeek/logs/current/conn.log",
    "/var/log/zeek/current/conn.log",
    "/usr/local/zeek/logs/current/conn.log",
    "./conn.log"
]

CONFIGURED_PATH = os.getenv("ZEEK_LOG_PATH", "")
if CONFIGURED_PATH:
    ZEEK_LOG_PATH = Path(CONFIGURED_PATH)
else:
    # Auto-detect first existing location or default to /opt/zeek/logs/current/conn.log
    detected = next((Path(p) for p in DEFAULT_LOG_PATHS if Path(p).exists()), Path("/opt/zeek/logs/current/conn.log"))
    ZEEK_LOG_PATH = detected

OFFSET_FILE = Path("/tmp/nids_sensor_agent_offset.dat")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nids.sensor_collector")

app = FastAPI(
    title="NIDS Zeek Sensor Collector",
    description="Lightweight edge telemetry daemon for reading and streaming Zeek connection logs.",
    version="1.0.0"
)

# In-memory offset tracker
file_offset: int = 0

def load_saved_offset() -> int:
    global file_offset
    if OFFSET_FILE.exists():
        try:
            val = int(OFFSET_FILE.read_text().strip())
            file_offset = max(0, val)
        except Exception:
            file_offset = 0
    return file_offset

def save_offset(offset: int) -> None:
    global file_offset
    file_offset = offset
    try:
        OFFSET_FILE.write_text(str(offset))
    except Exception as e:
        logger.warning(f"Could not persist offset file: {e}")

load_saved_offset()

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header."
        )

def parse_zeek_line(line: str, headers: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    """Parse a single line from conn.log supporting both JSON format and TSV format."""
    clean = line.strip()
    if not clean or clean.startswith("#"):
        return None

    # 1. Attempt JSON parsing
    if clean.startswith("{") and clean.endswith("}"):
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

    # 2. Attempt TSV (Tab-Separated Values) format with known headers
    if headers and "\t" in clean:
        parts = clean.split("\t")
        if len(parts) == len(headers):
            record: Dict[str, Any] = {}
            for k, v in zip(headers, parts):
                if v == "-":
                    record[k] = None
                else:
                    record[k] = v
            return record

    return None

def extract_tsv_headers(filepath: Path) -> List[str]:
    """Extract column header names from TSV format Zeek conn.log."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for _ in range(25):
                line = f.readline()
                if not line:
                    break
                if line.startswith("#fields"):
                    parts = line.strip().split("\t")
                    # Header line is: #fields <col1> <col2> ...
                    if len(parts) > 1:
                        return parts[1:]
                    # Space separated fallback
                    space_parts = line.strip().split()
                    if len(space_parts) > 1:
                        return space_parts[1:]
    except Exception as e:
        logger.warning(f"Error reading TSV headers: {e}")
    return []

@app.get("/")
def root():
    return {
        "service": "NIDS Zeek Sensor Agent",
        "status": "online",
        "zeek_log_path": str(ZEEK_LOG_PATH),
        "log_exists": ZEEK_LOG_PATH.exists()
    }

@app.get("/health")
def health():
    size = ZEEK_LOG_PATH.stat().st_size if ZEEK_LOG_PATH.exists() else 0
    return {
        "status": "online",
        "zeek_log_path": str(ZEEK_LOG_PATH),
        "file_exists": ZEEK_LOG_PATH.exists(),
        "file_size_bytes": size,
        "current_offset": file_offset
    }

@app.get("/logs")
def get_logs(x_api_key: Optional[str] = Header(None)):
    """
    Fetch all newly appended Zeek connection records since last read offset.
    Updates the read pointer so records are ingested incrementally.
    """
    verify_api_key(x_api_key)

    if not ZEEK_LOG_PATH.exists():
        logger.warning(f"Zeek log file not found at: {ZEEK_LOG_PATH}")
        return []

    tsv_headers = extract_tsv_headers(ZEEK_LOG_PATH)
    logs: List[Dict[str, Any]] = []

    try:
        with open(ZEEK_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            # If file was rotated/truncated, reset offset to beginning
            f.seek(0, os.SEEK_END)
            current_size = f.tell()

            global file_offset
            if file_offset > current_size:
                logger.info("Log file truncation/rotation detected. Resetting offset to 0.")
                file_offset = 0

            f.seek(file_offset)

            for line in f:
                parsed = parse_zeek_line(line, tsv_headers)
                if parsed:
                    logs.append(parsed)

            new_offset = f.tell()
            save_offset(new_offset)

        logger.info(f"Read {len(logs)} new Zeek records. Offset updated: {file_offset} -> {new_offset}")
        return logs

    except Exception as e:
        logger.error(f"Error reading Zeek log file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read sensor logs: {str(e)}"
        )

@app.delete("/logs")
def reset_logs(x_api_key: Optional[str] = Header(None)):
    """Reset the log read pointer to 0 and optionally truncate log buffer."""
    verify_api_key(x_api_key)
    save_offset(0)
    logger.info("Reset sensor offset to 0.")
    return {"status": "success", "message": "Sensor log read cursor reset to 0."}

if __name__ == "__main__":
    logger.info(f"Starting Sensor Collector on {AGENT_HOST}:{AGENT_PORT} watching '{ZEEK_LOG_PATH}'...")
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)
