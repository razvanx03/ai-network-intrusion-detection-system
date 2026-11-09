from app.routes.deps import get_current_user
from datetime import date
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.constants import VALID_ALERT_STATUSES, ALERT_ROUTE_PREFIX
from app.database.session import get_db
from app.schemas.alert import AlertResponse, AlertFilter, AlertStatsResponse, AlertStatusUpdate, DailyAlertsResponse
from app.services.alert_service import AlertService
from app.schemas.alert import AlertBulkStatusUpdate

router = APIRouter(prefix=ALERT_ROUTE_PREFIX, tags=["Intrusion Alerts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
def get_alerts(
    attack_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE"),
    src_ip: Optional[str] = Query(None),
    provenance: Literal["analysis"] | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False),
    archived_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """List intrusion detection alerts with filtering and pagination."""
    service = AlertService(db)
    filters = AlertFilter(
        provenance=provenance,
        attack_type=attack_type,
        status=status,
        src_ip=src_ip,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        archived_only=archived_only
    )
    items, total = service.get_alerts(filters)
    return {
        "items": [AlertResponse.model_validate(a) for a in items],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats", response_model=AlertStatsResponse)
def get_alert_stats(provenance: Literal["analysis"] | None = Query(None), db: Session = Depends(get_db)):
    """Aggregate statistics for alerts dashboard (counts, severities, top attack types)."""
    service = AlertService(db)
    return service.get_stats(provenance)


@router.get("/export")
def export_alerts(
    format: str = Query("csv", pattern="^(csv|json)$"),
    provenance: Literal["analysis"] | None = Query(None),
    db: Session = Depends(get_db)
):
    """Export alerts as CSV or JSON report for incident response and auditing."""
    from fastapi.responses import Response, JSONResponse
    service = AlertService(db)
    if format == "csv":
        csv_content = service.export_alerts_csv(provenance)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nids_alerts_report.csv"}
        )
    else:
        json_content = service.export_alerts_json(provenance)
        return JSONResponse(
            content=json_content,
            headers={"Content-Disposition": "attachment; filename=nids_alerts_report.json"}
        )


@router.get("/daily", response_model=DailyAlertsResponse)
def daily_alerts(period_start: date, timezone: str = Query(min_length=1, max_length=100),
                 period: Literal["week", "month"] = Query("week"), db: Session = Depends(get_db)):
    try:
        return AlertService(db).get_daily_counts(period_start, timezone, period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/status", response_model=dict[str, int])
def update_many_statuses(payload: AlertBulkStatusUpdate, db: Session = Depends(get_db)):
    try:
        return AlertService(db).update_many_statuses(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Selected findings are unavailable; no status was changed") from exc


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update status of an alert (e.g., mark as RESOLVED or FALSE_POSITIVE)."""
    if payload.status.upper() not in VALID_ALERT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {sorted(list(VALID_ALERT_STATUSES))}",
        )
    service = AlertService(db)
    updated = service.update_alert_status(alert_id, payload.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found.",
        )
    return AlertResponse.model_validate(updated)
