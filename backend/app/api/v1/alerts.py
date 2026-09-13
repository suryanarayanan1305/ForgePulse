"""
api/v1/alerts.py — Operational Alert Endpoints
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.alert import AlertAcknowledgeRequest, AlertResponse
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse], summary="List Active Alerts")
async def list_alerts(
    machine_id: Optional[str] = Query(default=None, description="Filter by machine ID"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    """Returns currently open operational alerts across the plant floor."""
    return await alert_service.get_active_alerts(db, machine_id=machine_id.upper() if machine_id else None, limit=limit)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Acknowledge Alert")
async def acknowledge_alert(
    alert_id: UUID,
    body: AlertAcknowledgeRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Marks an alert as acknowledged by an operator."""
    alert = await alert_service.acknowledge_alert(db, alert_id, acknowledged_by=body.acknowledged_by)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found",
        )
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse, summary="Resolve Alert")
async def resolve_alert(alert_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Marks an alert as resolved."""
    alert = await alert_service.resolve_alert(db, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found",
        )
    return alert
