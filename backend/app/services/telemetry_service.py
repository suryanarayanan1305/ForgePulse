"""
services/telemetry_service.py — Telemetry Ingestion, Anomaly Detection & Persistence Pipeline
=============================================================================================

EXECUTION PIPELINE PER TELEMETRY MESSAGE:
  1. Validate incoming payload against Machine limit thresholds (Level 1 Anomaly)
  2. Evaluate rolling Z-score statistical anomalies (Level 2 Anomaly)
  3. Evaluate IsolationForest multivariate ML anomaly model (Level 3 Anomaly)
  4. Trigger AlertService if anomalies or threshold breaches are detected
  5. Update Machine state and trigger DowntimeTracker on status transitions
  6. Insert Telemetry record into PostgreSQL
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Optional
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine import Machine
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryIngest, TelemetryResponse
from app.analytics.statistical import statistical_detector
from app.analytics.ml_model import ml_anomaly_detector
from app.analytics.downtime import downtime_tracker
from app.services.alert_service import alert_service

logger = logging.getLogger(__name__)


class TelemetryService:
    """Core telemetry processing and analytical dispatch pipeline."""

    async def process_and_persist_telemetry(
        self,
        db: AsyncSession,
        data: TelemetryIngest,
    ) -> Telemetry:
        """
        Processes a single validated telemetry reading from the MQTT stream.
        """
        # 1. Fetch Machine metadata and operating limits
        stmt = select(Machine).where(Machine.machine_id == data.machine_id)
        machine = (await db.execute(stmt)).scalar_one_or_none()

        temp_limit = float(machine.temperature_limit) if machine else 85.0
        vib_limit = float(machine.vibration_limit) if machine else 8.0
        pres_limit = float(machine.pressure_limit) if machine else 12.0

        is_anomaly = False
        anomaly_score = 0.0

        # --- LEVEL 1: Static Threshold Checks ---
        if data.temperature is not None and data.temperature > temp_limit:
            is_anomaly = True
            await alert_service.raise_alert_if_not_suppressed(
                db,
                machine_id=data.machine_id,
                alert_type="HIGH_TEMPERATURE",
                severity="CRITICAL" if data.temperature > (temp_limit + 5.0) else "WARNING",
                message=f"Spindle temperature {data.temperature:.1f}°C breached limit ({temp_limit}°C)",
                metric_name="temperature",
                observed_value=data.temperature,
                threshold_value=temp_limit,
            )

        if data.vibration is not None and data.vibration > vib_limit:
            is_anomaly = True
            await alert_service.raise_alert_if_not_suppressed(
                db,
                machine_id=data.machine_id,
                alert_type="HIGH_VIBRATION",
                severity="CRITICAL" if data.vibration > (vib_limit + 2.0) else "WARNING",
                message=f"Vibration {data.vibration:.3f} mm/s breached limit ({vib_limit} mm/s)",
                metric_name="vibration",
                observed_value=data.vibration,
                threshold_value=vib_limit,
            )

        if data.pressure is not None and data.pressure > pres_limit:
            is_anomaly = True
            await alert_service.raise_alert_if_not_suppressed(
                db,
                machine_id=data.machine_id,
                alert_type="PRESSURE_ANOMALY",
                severity="WARNING",
                message=f"Pressure {data.pressure:.2f} bar breached limit ({pres_limit} bar)",
                metric_name="pressure",
                observed_value=data.pressure,
                threshold_value=pres_limit,
            )

        # --- LEVEL 2: Statistical Z-Score Detection ---
        stat_anomaly_vib, z_vib, _, _ = statistical_detector.push_and_evaluate(
            data.machine_id, "vibration", data.vibration
        )
        stat_anomaly_temp, z_temp, _, _ = statistical_detector.push_and_evaluate(
            data.machine_id, "temperature", data.temperature
        )

        if (stat_anomaly_vib or stat_anomaly_temp) and not is_anomaly:
            is_anomaly = True
            anomaly_score = float(max(abs(z_vib), abs(z_temp)))
            await alert_service.raise_alert_if_not_suppressed(
                db,
                machine_id=data.machine_id,
                alert_type="STATISTICAL_ANOMALY",
                severity="WARNING",
                message=f"Statistical anomaly detected (Z-Score: {anomaly_score:.2f})",
                metric_name="vibration" if stat_anomaly_vib else "temperature",
                observed_value=data.vibration if stat_anomaly_vib else data.temperature,
            )

        # --- LEVEL 3: Multivariate ML (IsolationForest) ---
        ml_anomaly, ml_score = ml_anomaly_detector.predict(
            temperature=data.temperature,
            vibration=data.vibration,
            pressure=data.pressure,
            rpm=data.rpm,
            power_consumption=data.power_consumption,
        )
        if ml_anomaly:
            is_anomaly = True
            anomaly_score = float(ml_score)

        # --- Update Machine Live State ---
        if machine:
            machine.current_status = data.machine_status or "STOPPED"
            machine.last_seen_at = data.timestamp

        # --- State Machine & Downtime Tracking ---
        await downtime_tracker.handle_status_transition(
            db,
            machine_id=data.machine_id,
            new_status=data.machine_status or "STOPPED",
            timestamp=data.timestamp,
            error_code=data.error_code,
        )

        # --- Persist Telemetry Record ---
        telemetry = Telemetry(
            machine_id=data.machine_id,
            plant_id=data.plant_id,
            timestamp=data.timestamp,
            temperature=Decimal(str(round(data.temperature, 2))) if data.temperature is not None else None,
            pressure=Decimal(str(round(data.pressure, 2))) if data.pressure is not None else None,
            vibration=Decimal(str(round(data.vibration, 3))) if data.vibration is not None else None,
            rpm=Decimal(str(round(data.rpm, 2))) if data.rpm is not None else None,
            power_consumption=Decimal(str(round(data.power_consumption, 3))) if data.power_consumption is not None else None,
            production_count=data.production_count or 0,
            machine_status=data.machine_status,
            error_code=data.error_code,
            is_anomaly=is_anomaly,
            anomaly_score=Decimal(str(round(anomaly_score, 4))) if anomaly_score else None,
        )
        db.add(telemetry)
        await db.flush()
        return telemetry

    async def get_latest_telemetry(self, db: AsyncSession, machine_id: str) -> Optional[Telemetry]:
        stmt = (
            select(Telemetry)
            .where(Telemetry.machine_id == machine_id)
            .order_by(desc(Telemetry.timestamp))
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_recent_history(
        self, db: AsyncSession, machine_id: str, limit: int = 60
    ) -> List[Telemetry]:
        stmt = (
            select(Telemetry)
            .where(Telemetry.machine_id == machine_id)
            .order_by(desc(Telemetry.timestamp))
            .limit(limit)
        )
        result = await db.execute(stmt)
        # Reverse to chronological ascending order for charting
        return list(reversed(result.scalars().all()))


telemetry_service = TelemetryService()
