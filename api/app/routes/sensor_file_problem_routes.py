from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.routes.deps import get_current_user
from app.schemas.sensor import SensorFileProblemPage
from app.services.sensor_file_problem_service import SensorFileProblemService, ProblemNotFoundError, ProblemNotBlockedError
from app.services.analysis_service import AnalysisBusyError
from app.repositories.reset_repository import ResetBusyError

router = APIRouter(prefix="/system/import-problems", tags=["Import problems"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SensorFileProblemPage)
def problems(limit: int = Query(20, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return SensorFileProblemService(db).page(limit, offset)


@router.post("/{problem_id}/retry")
def retry(problem_id: str, db: Session = Depends(get_db)):
    try:
        return SensorFileProblemService(db).retry(problem_id)
    except ProblemNotFoundError as exc:
        raise HTTPException(404, {"code": "import_problem_missing"}) from exc
    except ProblemNotBlockedError as exc:
        raise HTTPException(409, {"code": "import_problem_not_blocked"}) from exc
    except AnalysisBusyError as exc:
        raise HTTPException(409, {"code": "analysis_busy"}) from exc
    except ResetBusyError as exc:
        raise HTTPException(409, {"code": "reset_pending"}) from exc
