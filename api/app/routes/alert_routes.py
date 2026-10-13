from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.constants import VALID_ALERT_STATUSES, ALERT_ROUTE_PREFIX
from app.database.session import get_db
from app.schemas.alert import AlertResponse, AlertFilter, AlertStatsResponse, AlertStatusUpdate
from app.services.alert_service import AlertService

router = APIRouter(prefix=ALERT_ROUTE_PREFIX, tags=["Intrusion Alerts"])


@router.get("", response_model=dict)
def get_alerts(
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    attack_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE"),
    src_ip: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List intrusion detection alerts with filtering and pagination."""
    service = AlertService(db)
    filters = AlertFilter(
        severity=severity,
        attack_type=attack_type,
        status=status,
        src_ip=src_ip,
        limit=limit,
        offset=offset
    )
    items, total = service.get_alerts(filters)
    return {
        "items": [AlertResponse.model_validate(a) for a in items],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats", response_model=AlertStatsResponse)
def get_alert_stats(db: Session = Depends(get_db)):
    """Aggregate statistics for alerts dashboard (counts, severities, top attack types)."""
    service = AlertService(db)
    return service.get_stats()


@router.get("/export")
def export_alerts(
    format: str = Query("csv", pattern="^(csv|json)$"),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Export alerts as CSV or JSON report for incident response and auditing."""
    from fastapi.responses import Response, JSONResponse
    service = AlertService(db)
    if format == "csv":
        csv_content = service.export_alerts_csv(severity)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nids_alerts_report.csv"}
        )
    else:
        json_content = service.export_alerts_json(severity)
        return JSONResponse(
            content=json_content,
            headers={"Content-Disposition": "attachment; filename=nids_alerts_report.json"}
        )


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
