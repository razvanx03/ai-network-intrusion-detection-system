from app.routes.deps import get_current_user
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.constants import (
    SYSTEM_ROUTE_PREFIX,
    SENSOR_MODE_MOCK,
    SENSOR_MODE_REMOTE,
)
from app.database.session import get_db
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.schemas.system import (
    SystemHealthResponse,
    FetchAnalyzeResponse,
    SensorResetResponse,
)
from app.services.system_service import SystemService

router = APIRouter(prefix=SYSTEM_ROUTE_PREFIX, tags=["System & Sensor Operations"], dependencies=[Depends(get_current_user)])


@router.post("/fetch-and-analyze", response_model=FetchAnalyzeResponse)
async def fetch_and_analyze(db: Session = Depends(get_db)):
    """
    On-Demand Trigger:
    Pulls new Zeek logs from sensor agent (or mock dataset), runs AI & heuristic analysis,
    persists records and alerts into database, and returns analysis summary.
    """
    service = SystemService(db)
    result = await service.fetch_and_analyze()
    return result


@router.post("/reset-sensor", response_model=SensorResetResponse)
async def reset_sensor(db: Session = Depends(get_db)):
    """Reset read cursors on the remote Zeek sensor (or reset mock stream)."""
    service = SystemService(db)
    return await service.reset_sensor()


@router.post("/clear-database")
def clear_database(db: Session = Depends(get_db)):
    """Wipe connections and alerts from local SQLite DB for a clean demo run."""
    service = SystemService(db)
    return service.clear_database_all()


@router.get("/health", response_model=SystemHealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint indicating sensor mode and DB status."""
    conn_repo = ConnectionRepository(db)
    alert_repo = AlertRepository(db)
    return {
        "status": "healthy",
        "database": "connected",
        "sensor_mode": SENSOR_MODE_MOCK if settings.SENSOR_MOCK_MODE else SENSOR_MODE_REMOTE,
        "connections_total": conn_repo.count_total(),
        "alerts_total": alert_repo.count_total(),
    }
