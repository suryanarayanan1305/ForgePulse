"""
api/v1/analytics.py — Production KPIs & Metric Trends Endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.machine import Machine
from app.models.telemetry import Telemetry
from app.models.downtime import DowntimeLog
from app.schemas.analytics import (
    MetricTrendResponse,
    OEEMetrics,
    PlantProductionSummary,
    TrendPoint,
    DowntimeSummary,
)
from app.analytics.oee import calculate_machine_oee
from app.services.machine_service import machine_service

router = APIRouter(prefix="/analytics", tags=["Production Analytics & KPIs"])


@router.get("/summary", response_model=PlantProductionSummary, summary="Plant Operations Summary")
async def get_plant_summary(db: AsyncSession = Depends(get_async_session)):
    """Returns top-level plant KPIs (Machine counts, OEE, Average Health, Alerts)."""
    return await machine_service.get_plant_summary(db)


@router.get("/oee/{machine_id}", response_model=OEEMetrics, summary="Machine OEE Metrics")
async def get_machine_oee(
    machine_id: str,
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
    db: AsyncSession = Depends(get_async_session),
):
    """Calculates Availability, Performance, Quality, and OEE for a specific asset."""
    machine = await machine_service.get_machine_by_id(db, machine_id.upper())
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id.upper()}' not found",
        )
    return await calculate_machine_oee(db, machine_id.upper(), window_hours=window_hours)


@router.get("/trends/{machine_id}/{metric}", response_model=MetricTrendResponse, summary="Metric Historical Trend")
async def get_metric_trends(
    machine_id: str,
    metric: str,
    limit: int = Query(default=60, ge=10, le=300),
    db: AsyncSession = Depends(get_async_session),
):
    """Returns formatted historical time-series points with limits for charts."""
    machine = await machine_service.get_machine_by_id(db, machine_id.upper())
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Machine '{machine_id.upper()}' not found")

    metric = metric.lower()
    valid_metrics = {"temperature": ("°C", float(machine.temperature_limit)), "vibration": ("mm/s", float(machine.vibration_limit)), "pressure": ("bar", float(machine.pressure_limit)), "rpm": ("RPM", float(machine.rated_rpm or 6000))}
    if metric not in valid_metrics:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid metric '{metric}'. Valid: {list(valid_metrics.keys())}")

    unit, limit_val = valid_metrics[metric]

    stmt = select(Telemetry).where(Telemetry.machine_id == machine_id.upper()).order_by(desc(Telemetry.timestamp)).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    points = []
    for r in reversed(rows):
        val = getattr(r, metric, None)
        if val is not None:
            points.append(TrendPoint(timestamp=r.timestamp, value=float(val), is_anomaly=r.is_anomaly))

    return MetricTrendResponse(
        machine_id=machine_id.upper(),
        metric_name=metric,
        unit=unit,
        limit_value=limit_val,
        data_points=points,
    )
