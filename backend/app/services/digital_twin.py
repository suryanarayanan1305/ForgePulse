"""
services/digital_twin.py — Digital Twin Engine & Maintenance-Risk Estimator
=============================================================================

DIGITAL TWIN SYNTHESIS:
  Aggregates:
    - Machine Static Identity & Physical Limits
    - Real-Time Live Telemetry Reading
    - Machine Health Score Breakdown
    - Prototype Maintenance-Risk Estimation
    - 24-Hour Production & Downtime Summary
    - Active Operational Alerts
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine import Machine
from app.models.telemetry import Telemetry
from app.models.alert import Alert
from app.models.downtime import DowntimeLog
from app.schemas.digital_twin import (
    DigitalTwinResponse,
    MachineIdentity,
    PredictiveMaintenanceInsight,
    ProductionSummary,
)
from app.schemas.telemetry import TelemetryResponse
from app.schemas.alert import AlertResponse
from app.services.health_score import calculate_machine_health
from app.services.telemetry_service import telemetry_service
from app.services.alert_service import alert_service

logger = logging.getLogger(__name__)


class DigitalTwinService:
    """Aggregates and synthesizes the unified Digital Twin representation."""

    async def get_digital_twin(self, db: AsyncSession, machine_id: str) -> Optional[DigitalTwinResponse]:
        # 1. Fetch Machine Model
        stmt = select(Machine).where(Machine.machine_id == machine_id)
        machine = (await db.execute(stmt)).scalar_one_or_none()
        if not machine:
            return None

        # 2. Fetch Latest Telemetry
        latest_telem = await telemetry_service.get_latest_telemetry(db, machine_id)

        # 3. Calculate Transparent Health Score
        temp = float(latest_telem.temperature) if (latest_telem and latest_telem.temperature is not None) else None
        vib = float(latest_telem.vibration) if (latest_telem and latest_telem.vibration is not None) else None
        pres = float(latest_telem.pressure) if (latest_telem and latest_telem.pressure is not None) else None
        err = latest_telem.error_code if latest_telem else None

        health = calculate_machine_health(
            temperature=temp,
            temp_limit=float(machine.temperature_limit),
            vibration=vib,
            vib_limit=float(machine.vibration_limit),
            pressure=pres,
            pres_limit=float(machine.pressure_limit),
            status=machine.current_status,
            error_code=err,
        )

        # 4. Fetch Active Alerts
        active_alerts = await alert_service.get_active_alerts(db, machine_id=machine_id, limit=10)

        # 5. Production & Downtime Summary (Cumulative / 24h)
        total_parts = latest_telem.production_count if (latest_telem and latest_telem.production_count) else 0

        downtime_stmt = select(func.coalesce(func.sum(DowntimeLog.duration_seconds), 0)).where(
            and_(DowntimeLog.machine_id == machine_id, DowntimeLog.ended_at.is_not(None))
        )
        total_downtime_sec = (await db.execute(downtime_stmt)).scalar_one()
        downtime_min = total_downtime_sec / 60.0

        production = ProductionSummary(
            total_parts=int(total_parts),
            operating_hours=round(max(0.0, 24.0 - (downtime_min / 60.0)), 1),
            downtime_minutes=round(downtime_min, 1),
            current_run_duration_minutes=round(max(0.0, 120.0 - (downtime_min % 60.0)), 1),
        )

        # 6. Prototype Maintenance-Risk Estimation
        signals = []
        risk_score = 0.0

        if vib and vib > float(machine.vibration_limit) * 0.75:
            signals.append(f"Elevated vibration ({vib:.2f} mm/s)")
            risk_score += 35.0

        if temp and temp > float(machine.temperature_limit) * 0.85:
            signals.append(f"Temperature above baseline ({temp:.1f} °C)")
            risk_score += 25.0

        if len(active_alerts) > 0:
            signals.append(f"{len(active_alerts)} active alerts in queue")
            risk_score += 20.0

        if machine.current_status == "FAULT":
            signals.append("Machine currently in FAULT state")
            risk_score += 30.0

        risk_score = min(100.0, risk_score)
        if risk_score >= 70.0:
            risk_level = "CRITICAL"
            recommendation = "Immediate shutdown and mechanical inspection required."
        elif risk_score >= 40.0:
            risk_level = "HIGH"
            recommendation = "Schedule maintenance technician inspection within 24 hours."
        elif risk_score >= 20.0:
            risk_level = "MEDIUM"
            recommendation = "Monitor thermal and vibration trends closely over next shift."
        else:
            risk_level = "LOW"
            recommendation = "Asset operating within nominal parameters. Routine inspection as scheduled."

        prediction = PredictiveMaintenanceInsight(
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            signals=signals,
            recommendation=recommendation,
        )

        identity = MachineIdentity(
            machine_id=machine.machine_id,
            machine_name=machine.machine_name,
            machine_type=machine.machine_type,
            plant_id=machine.plant_id,
            location=machine.location,
            manufacturer=machine.manufacturer,
            model=machine.model,
            rated_rpm=float(machine.rated_rpm) if machine.rated_rpm else None,
            temperature_limit=float(machine.temperature_limit),
            vibration_limit=float(machine.vibration_limit),
            pressure_limit=float(machine.pressure_limit),
            power_limit=float(machine.power_limit) if machine.power_limit else None,
        )

        latest_resp = None
        if latest_telem:
            latest_resp = TelemetryResponse(
                telemetry_id=latest_telem.telemetry_id,
                machine_id=latest_telem.machine_id,
                plant_id=latest_telem.plant_id,
                timestamp=latest_telem.timestamp,
                temperature=float(latest_telem.temperature) if latest_telem.temperature is not None else None,
                pressure=float(latest_telem.pressure) if latest_telem.pressure is not None else None,
                vibration=float(latest_telem.vibration) if latest_telem.vibration is not None else None,
                rpm=float(latest_telem.rpm) if latest_telem.rpm is not None else None,
                power_consumption=float(latest_telem.power_consumption) if latest_telem.power_consumption is not None else None,
                production_count=latest_telem.production_count,
                machine_status=latest_telem.machine_status,
                error_code=latest_telem.error_code,
                is_anomaly=latest_telem.is_anomaly,
                anomaly_score=float(latest_telem.anomaly_score) if latest_telem.anomaly_score else None,
                created_at=latest_telem.created_at,
            )

        alert_responses = [
            AlertResponse(
                alert_id=a.alert_id,
                machine_id=a.machine_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                metric_name=a.metric_name,
                observed_value=float(a.observed_value) if a.observed_value is not None else None,
                threshold_value=float(a.threshold_value) if a.threshold_value is not None else None,
                status=a.status,
                acknowledged_at=a.acknowledged_at,
                acknowledged_by=a.acknowledged_by,
                resolved_at=a.resolved_at,
                timestamp=a.timestamp,
                created_at=a.created_at,
            )
            for a in active_alerts
        ]

        return DigitalTwinResponse(
            identity=identity,
            current_status=machine.current_status,
            health=health,
            maintenance_prediction=prediction,
            production=production,
            latest_telemetry=latest_resp,
            active_alerts=alert_responses,
            last_seen=machine.last_seen_at,
            twin_timestamp=datetime.now(timezone.utc),
        )


digital_twin_service = DigitalTwinService()
