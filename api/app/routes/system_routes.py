from app.routes.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
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
    OverviewResponse,
    SensorStatusResponse,
)
from app.services.system_service import SystemService
from app.repositories.sensor_cursor_repository import CursorConflictError
from app.models.user import User
from app.services.analysis_service import AnalysisBusyError, AnalysisRunError
from app.routes.analysis_routes import run_error
from app.schemas.reset import ResetRequest, ResetStatus
from app.repositories.reset_repository import ResetRepository, ResetBusyError
from app.services.reset_service import ResetService
from app.integrations.sensor_client import SensorResetError

router = APIRouter(prefix=SYSTEM_ROUTE_PREFIX, tags=["System & Sensor Operations"], dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)):
    return SystemService(db).overview()


@router.get("/sensor-status", response_model=SensorStatusResponse)
async def sensor_status(db: Session = Depends(get_db)):
    return await SystemService(db).sensor_status()


@router.post("/fetch-and-analyze", response_model=FetchAnalyzeResponse)
async def fetch_and_analyze(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    On-Demand Trigger:
    Creates a durable session, imports/prepares new records and calls the detector boundary.
    """
    service = SystemService(db)
    try:
        return await service.fetch_and_analyze(user.id)
    except AnalysisBusyError as exc:
        raise HTTPException(409, "An analysis is already running.") from exc
    except ResetBusyError as exc:
        raise HTTPException(409, {"code": "reset_pending"}) from exc
    except AnalysisRunError as exc:
        raise run_error(exc) from exc
    except CursorConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/reset-status", response_model=ResetStatus)
def reset_status(db: Session = Depends(get_db)):
    operation = ResetRepository(db).running()
    return {"pending": operation is not None, "operation_id": operation.id if operation else None}


@router.post("/reset-data")
async def reset_data(request: ResetRequest, db: Session = Depends(get_db)):
    try:
        return await ResetService(db).run(request.operation_id)
    except AnalysisBusyError as exc:
        raise HTTPException(409, {"code": "analysis_busy"}) from exc
    except ResetBusyError as exc:
        raise HTTPException(409, {"code": "reset_pending"}) from exc
    except SensorResetError as exc:
        raise HTTPException(503, {"code": exc.code}) from exc






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
