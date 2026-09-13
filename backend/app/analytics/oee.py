"""
analytics/oee.py — Demonstrative Overall Equipment Effectiveness (OEE) Engine
=============================================================================

Calculates standard manufacturing KPIs:
  1. Availability = (Operating Time / Planned Production Time)
  2. Performance  = (Actual Production Rate / Ideal Production Rate)
  3. Quality      = (Good Parts / Total Parts Produced)
  4. OEE          = Availability * Performance * Quality

INTERVIEW CONTEXT:
  "OEE is the gold standard metric in manufacturing operations.
   - Availability accounts for unplanned and planned downtime.
   - Performance accounts for micro-stoppages and running below rated speed.
   - Quality accounts for defective parts and scrap rate.
   In ForgePulse, we compute these dynamically from SQL aggregates over
   telemetry and downtime logs."
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine import Machine
from app.models.telemetry import Telemetry
from app.models.downtime import DowntimeLog
from app.schemas.analytics import OEEMetrics


async def calculate_machine_oee(
    db: AsyncSession,
    machine_id: str,
    window_hours: float = 24.0,
) -> OEEMetrics:
    """
    Calculates 24-hour rolling OEE metrics for a specific machine.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    planned_minutes = window_hours * 60.0

    # 1. Query Total Downtime in Window
    downtime_stmt = select(func.coalesce(func.sum(DowntimeLog.duration_seconds), 0)).where(
        and_(
            DowntimeLog.machine_id == machine_id,
            DowntimeLog.started_at >= cutoff,
            DowntimeLog.ended_at.is_not(None),
        )
    )
    closed_downtime_seconds = (await db.execute(downtime_stmt)).scalar_one()

    # Check for active ongoing downtime
    open_downtime_stmt = select(DowntimeLog.started_at).where(
        and_(DowntimeLog.machine_id == machine_id, DowntimeLog.ended_at.is_(None))
    )
    open_start = (await db.execute(open_downtime_stmt)).scalar_one_or_none()
    ongoing_seconds = 0
    if open_start:
        effective_start = max(open_start, cutoff)
        ongoing_seconds = max(0, int((now - effective_start).total_seconds()))

    total_downtime_minutes = (closed_downtime_seconds + ongoing_seconds) / 60.0
    total_downtime_minutes = min(planned_minutes, total_downtime_minutes)
    operating_minutes = max(0.0, planned_minutes - total_downtime_minutes)

    # Availability %
    availability = (operating_minutes / planned_minutes) * 100.0 if planned_minutes > 0 else 100.0

    # 2. Query Production Count & Average RPM
    telemetry_stmt = select(
        func.count(Telemetry.telemetry_id),
        func.coalesce(func.max(Telemetry.production_count), 0),
        func.coalesce(func.avg(Telemetry.rpm), 0.0),
    ).where(and_(Telemetry.machine_id == machine_id, Telemetry.timestamp >= cutoff))
    res = (await db.execute(telemetry_stmt)).one()
    sample_count, total_production_count, avg_rpm = res[0], int(res[1]), float(res[2])

    # Machine rated RPM
    machine_stmt = select(Machine.rated_rpm).where(Machine.machine_id == machine_id)
    rated_rpm_res = (await db.execute(machine_stmt)).scalar_one_or_none()
    rated_rpm = float(rated_rpm_res) if rated_rpm_res else 6000.0

    # Performance %: (Actual average operating speed vs rated speed)
    if rated_rpm > 0 and operating_minutes > 0 and avg_rpm > 0:
        performance = min(100.0, (avg_rpm / (rated_rpm * 0.85)) * 100.0)
    else:
        performance = 85.0 if operating_minutes > 0 else 0.0

    # Quality %: Simulated high-yield manufacturing (97% - 99.5% good parts)
    # Deduct slight scrap penalty if anomalies were logged
    anomaly_stmt = select(func.count(Telemetry.telemetry_id)).where(
        and_(Telemetry.machine_id == machine_id, Telemetry.timestamp >= cutoff, Telemetry.is_anomaly == True)
    )
    anomaly_count = (await db.execute(anomaly_stmt)).scalar_one()
    scrap_count = int(min(total_production_count, anomaly_count // 3))
    quality = ((total_production_count - scrap_count) / total_production_count * 100.0) if total_production_count > 0 else 99.0

    # Overall OEE
    oee = (availability / 100.0) * (performance / 100.0) * (quality / 100.0) * 100.0

    return OEEMetrics(
        availability=round(availability, 2),
        performance=round(performance, 2),
        quality=round(quality, 2),
        oee=round(oee, 2),
        planned_production_minutes=round(planned_minutes, 1),
        operating_minutes=round(operating_minutes, 1),
        downtime_minutes=round(total_downtime_minutes, 1),
        total_production_count=total_production_count,
        scrap_count=scrap_count,
    )
