from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.routes.deps import get_current_user
from app.schemas.analysis import AnalysisSessionResponse
from app.schemas.connection import ConnectionResponse
from app.services.analysis_service import AnalysisRunError
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis sessions"], dependencies=[Depends(get_current_user)])


def run_error(error: AnalysisRunError) -> HTTPException:
    status = {"invalid_records": 422, "sensor_unavailable": 502, "cursor_conflict": 409}.get(error.code, 500)
    return HTTPException(status, detail={"code": error.code, "analysis_session_id": error.session_id})


def require_session(repo: AnalysisRepository, session_id: str, include_archived: bool = False):
    session = repo.get(session_id)
    if session is None or (getattr(session, "archive_batch_id", None) is not None and not include_archived):
        raise HTTPException(404, "Analysis session not found.")
    return session


@router.get("")
def list_sessions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), include_archived: bool = Query(False),
                  archived_only: bool = Query(False), alerts_only: bool = Query(False), db: Session = Depends(get_db)):
    page = AnalysisRepository(db).page(limit, offset, include_archived, archived_only, alerts_only)
    page["items"] = [AnalysisSessionResponse.model_validate(item) for item in page["items"]]
    return page


@router.get("/{session_id}", response_model=AnalysisSessionResponse)
def get_session(session_id: str, include_archived: bool = Query(False), db: Session = Depends(get_db)):
    return require_session(AnalysisRepository(db), session_id, include_archived)


@router.get("/{session_id}/connections")
def session_connections(session_id: str, limit: int = Query(50, ge=1, le=500),
                        offset: int = Query(0, ge=0), include_archived: bool = Query(False), db: Session = Depends(get_db)):
    repo = AnalysisRepository(db)
    require_session(repo, session_id, include_archived)
    rows, total = repo.connection_page(session_id, limit, offset)
    context = ConnectionService(db).with_context([connection for connection, _ in rows])
    return {
        "items": [{"connection": connection,
                   "file_id": link.file_id, "file": link.file} for connection, (_, link) in zip(context, rows)],
        "total": total, "limit": limit, "offset": offset,
    }


@router.get("/{session_id}/alerts/{alert_id}/connections", response_model=list[ConnectionResponse])
def alert_sources(session_id: str, alert_id: int, include_archived: bool = Query(False), db: Session = Depends(get_db)):
    require_session(AnalysisRepository(db), session_id, include_archived)
    result = AnalysisRepository(db).alert_connections(session_id, alert_id)
    if result is None:
        raise HTTPException(404, "Alert not found in this analysis session.")
    return ConnectionService(db).with_context(result)
