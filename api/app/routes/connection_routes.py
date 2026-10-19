from app.routes.deps import get_current_user
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.constants import CONNECTION_ROUTE_PREFIX
from app.database.session import get_db
from app.schemas.connection import ConnectionResponse, ConnectionFilter
from app.services.connection_service import ConnectionService

router = APIRouter(prefix=CONNECTION_ROUTE_PREFIX, tags=["Network Logs"], dependencies=[Depends(get_current_user)])


@router.get("/connections")
def get_connections(
    src_ip: Optional[str] = Query(None, description="Filter by source IP"),
    dst_ip: Optional[str] = Query(None, description="Filter by destination IP"),
    proto: Optional[str] = Query(None, description="Filter by protocol (tcp, udp, icmp)"),
    conn_state: Optional[str] = Query(None, description="Filter by Zeek connection state"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve ingested Zeek network flow records with pagination and filters."""
    service = ConnectionService(db)
    filters = ConnectionFilter(
        src_ip=src_ip,
        dst_ip=dst_ip,
        proto=proto,
        conn_state=conn_state,
        limit=limit,
        offset=offset
    )
    items, total = service.get_connections(filters)
    return {
        "items": [ConnectionResponse.model_validate(c) for c in items],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
def get_log_stats(db: Session = Depends(get_db)):
    """Summary statistics about stored connections."""
    service = ConnectionService(db)
    return {
        "total_connections": service.count_total()
    }
