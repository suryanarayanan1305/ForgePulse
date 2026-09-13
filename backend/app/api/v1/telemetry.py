"""
api/v1/telemetry.py — Telemetry Endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.telemetry import TelemetryResponse
from app.services.telemetry_service import telemetry_service

router = APIRouter(prefix="/machines/{machine_id}/telemetry", tags=["Telemetry"])


@router.get("/latest", response_model=TelemetryResponse, summary="Get Latest Machine Telemetry")
async def get_latest_telemetry(machine_id: str, db: AsyncSession = Depends(get_async_session)):
    """Returns the most recent sensor reading received from the MQTT stream."""
    record = await telemetry_service.get_latest_telemetry(db, machine_id.upper())
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for machine '{machine_id.upper()}'",
        )
    return record


@router.get("/history", response_model=List[TelemetryResponse], summary="Get Recent Telemetry History")
async def get_telemetry_history(
    machine_id: str,
    limit: int = Query(default=60, ge=5, le=500, description="Number of recent readings"),
    db: AsyncSession = Depends(get_async_session),
):
    """Returns historical time-series telemetry points in chronological order for charting."""
    return await telemetry_service.get_recent_history(db, machine_id.upper(), limit=limit)
