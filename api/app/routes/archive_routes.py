from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.routes.deps import get_current_user
from app.repositories.archive_repository import ArchiveRepository
from app.schemas.archive import ArchiveBatchResponse, ArchivePage
from app.schemas.connection import ConnectionResponse
from app.schemas.analysis import AnalysisSessionResponse
from app.schemas.alert import AlertResponse
from app.services.archive_service import ArchiveService, EmptyArchiveError, ArchiveNotFoundError
from app.services.analysis_service import AnalysisBusyError
from app.models.archive_batch import ArchiveBatch
from app.repositories.archive_snapshot_repository import ArchiveSnapshotRepository
from app.schemas.protocol_event import ContextType, ProtocolEventResponse

router = APIRouter(prefix="/archives", tags=["Archives"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_archives(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    page = ArchiveRepository(db).page(limit, offset)
    page["items"] = [ArchiveBatchResponse.model_validate(item) for item in page["items"]]
    return page


def change(db, batch_id=None):
    try:
        return ArchiveService(db).change(batch_id)
    except AnalysisBusyError as exc:
        raise HTTPException(409, {"code": "analysis_busy"}) from exc
    except EmptyArchiveError as exc:
        raise HTTPException(409, {"code": "archive_empty"}) from exc
    except ArchiveNotFoundError as exc:
        raise HTTPException(404, {"code": "archive_not_found"}) from exc


@router.post("", response_model=ArchiveBatchResponse)
def archive_active_data(db: Session = Depends(get_db)):
    return change(db)


@router.post("/{batch_id}/restore", response_model=ArchiveBatchResponse)
def restore_archive(batch_id: str, db: Session = Depends(get_db)):
    return change(db, batch_id)


def require_batch(db, batch_id, snapshot=True):
    batch = db.get(ArchiveBatch, batch_id)
    if batch is None:
        raise HTTPException(404, {"code": "archive_not_found"})
    if snapshot and batch.snapshot_version != 1:
        raise HTTPException(409, {"code": "archive_snapshot_unavailable"})
    return batch


@router.get("/{batch_id}", response_model=ArchiveBatchResponse)
def get_archive(batch_id: str, db: Session = Depends(get_db)):
    return require_batch(db, batch_id, snapshot=False)


@router.get("/{batch_id}/protocols", response_model=list[str])
def batch_protocols(batch_id: str, db: Session = Depends(get_db)):
    require_batch(db, batch_id)
    return ArchiveSnapshotRepository(db).protocols(batch_id)


@router.get("/{batch_id}/connections", response_model=ArchivePage[ConnectionResponse])
def batch_connections(batch_id: str, limit: int = Query(20, ge=1, le=500), offset: int = Query(0, ge=0),
                      protocols: list[str] = Query(default=[], max_length=64), alerts_only: bool = False,
                      session_id: str | None = None, db: Session = Depends(get_db)):
    require_batch(db, batch_id)
    repo = ArchiveSnapshotRepository(db)
    if session_id and repo.record(batch_id, "session", session_id) is None:
        raise HTTPException(404, {"code": "archive_not_found"})
    return repo.page(batch_id, "connection", limit, offset, protocols, alerts_only, session_id)


@router.get("/{batch_id}/sessions", response_model=ArchivePage[AnalysisSessionResponse])
def batch_sessions(batch_id: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    require_batch(db, batch_id)
    return ArchiveSnapshotRepository(db).page(batch_id, "session", limit, offset)


def require_connection(db, batch_id, connection_id):
    require_batch(db, batch_id)
    repo = ArchiveSnapshotRepository(db)
    connection = repo.record(batch_id, "connection", connection_id)
    if connection is None:
        raise HTTPException(404, {"code": "archive_not_found"})
    return repo, connection


@router.get("/{batch_id}/connections/{connection_id}/events", response_model=ArchivePage[ProtocolEventResponse])
def batch_events(batch_id: str, connection_id: int, kind: ContextType,
                 limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    repo, connection = require_connection(db, batch_id, connection_id)
    return repo.page(batch_id, "event", limit, offset, uid=connection.payload["uid"], context=kind)


@router.get("/{batch_id}/connections/{connection_id}/alerts", response_model=ArchivePage[AlertResponse])
def batch_alerts(batch_id: str, connection_id: int, limit: int = Query(20, ge=1, le=100),
                 offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    repo, _ = require_connection(db, batch_id, connection_id)
    return repo.page(batch_id, "alert", limit, offset, uid=str(connection_id))
