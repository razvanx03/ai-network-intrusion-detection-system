from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.repositories.analysis_repository import AnalysisRepository
from app.routes.deps import get_current_user
from app.schemas.analysis import AnalysisRequest, AnalysisSessionResponse
from app.schemas.alert import AlertResponse
from app.schemas.connection import ConnectionResponse
from app.schemas.system import FetchAnalyzeResponse
from app.services.analysis_service import AnalysisBusyError, AnalysisRunError, AnalysisService

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis sessions"], dependencies=[Depends(get_current_user)])


def run_error(error: AnalysisRunError) -> HTTPException:
    status = {"invalid_records": 422, "sensor_unavailable": 502, "cursor_conflict": 409}.get(error.code, 500)
    return HTTPException(status, detail={"code": error.code, "analysis_session_id": error.session_id})


def require_session(repo: AnalysisRepository, session_id: str):
    session = repo.get(session_id)
    if session is None:
        raise HTTPException(404, "Analysis session not found.")
    return session


@router.post("", response_model=FetchAnalyzeResponse, status_code=201)
async def start_analysis(body: AnalysisRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return await AnalysisService(db).run(user.id, body)
    except AnalysisBusyError as exc:
        raise HTTPException(409, "An analysis is already running.") from exc
    except AnalysisRunError as exc:
        raise run_error(exc) from exc


@router.get("")
def list_sessions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    page = AnalysisRepository(db).page(limit, offset)
    page["items"] = [AnalysisSessionResponse.model_validate(item) for item in page["items"]]
    return page


@router.get("/{session_id}", response_model=AnalysisSessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return require_session(AnalysisRepository(db), session_id)


@router.get("/{session_id}/connections")
def session_connections(session_id: str, limit: int = Query(50, ge=1, le=500),
                        offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    repo = AnalysisRepository(db)
    require_session(repo, session_id)
    rows, total = repo.connection_page(session_id, limit, offset)
    return {
        "items": [{"connection": ConnectionResponse.model_validate(connection),
                   "file_id": link.file_id, "file": link.file} for connection, link in rows],
        "total": total, "limit": limit, "offset": offset,
    }


@router.get("/{session_id}/alerts")
def session_alerts(session_id: str, limit: int = Query(50, ge=1, le=500),
                   offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    repo = AnalysisRepository(db)
    require_session(repo, session_id)
    alerts, total = repo.alert_page(session_id, limit, offset)
    return {"items": [AlertResponse.model_validate(alert) for alert in alerts],
            "total": total, "limit": limit, "offset": offset}


@router.get("/{session_id}/alerts/{alert_id}/connections")
def alert_sources(session_id: str, alert_id: int, limit: int = Query(50, ge=1, le=500),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    result = AnalysisRepository(db).alert_connections(session_id, alert_id, limit, offset)
    if result is None:
        raise HTTPException(404, "Alert not found in this analysis session.")
    connections, total = result
    return {"items": [ConnectionResponse.model_validate(item) for item in connections],
            "total": total, "limit": limit, "offset": offset}
