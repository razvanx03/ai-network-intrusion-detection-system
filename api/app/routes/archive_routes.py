from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.routes.deps import get_current_user
from app.repositories.archive_repository import ArchiveRepository
from app.schemas.archive import ArchiveBatchResponse
from app.services.archive_service import ArchiveService, EmptyArchiveError, ArchiveNotFoundError
from app.services.analysis_service import AnalysisBusyError

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
