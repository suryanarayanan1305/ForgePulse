"""
services/machine_service.py — Machine Fleet Management & Overview
==================================================================
"""

from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.machine import Machine
from app.models.sensor import MachineSensor
from app.models.alert import Alert
from app.models.telemetry import Telemetry
from app.schemas.analytics import PlantProductionSummary
from app.analytics.oee import calculate_machine_oee


class MachineService:
    """Operations on the machine fleet."""

    async def get_all_machines(self, db: AsyncSession) -> List[Machine]:
        stmt = select(Machine).where(Machine.is_active == True).order_by(Machine.machine_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_machine_by_id(self, db: AsyncSession, machine_id: str) -> Optional[Machine]:
        stmt = (
            select(Machine)
            .where(and_(Machine.machine_id == machine_id, Machine.is_active == True))
            .options(selectinload(Machine.sensors))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_plant_summary(self, db: AsyncSession, plant_id: str = "PLANT-A") -> PlantProductionSummary:
        machines = await self.get_all_machines(db)
        total = len(machines)
        running = sum(1 for m in machines if m.current_status == "RUNNING")
        stopped = sum(1 for m in machines if m.current_status == "STOPPED")
        faults = sum(1 for m in machines if m.current_status == "FAULT")
        maintenance = sum(1 for m in machines if m.current_status == "MAINTENANCE")

        # Total parts across all machines
        prod_stmt = select(func.coalesce(func.sum(Telemetry.production_count), 0))
        # Cumulative maximum parts per machine
        total_parts = 0
        for m in machines:
            m_parts_stmt = select(func.coalesce(func.max(Telemetry.production_count), 0)).where(Telemetry.machine_id == m.machine_id)
            m_parts = (await db.execute(m_parts_stmt)).scalar_one()
            total_parts += int(m_parts)

        # Active alerts
        alert_stmt = select(func.count(Alert.alert_id)).where(Alert.status == "OPEN")
        active_alerts = (await db.execute(alert_stmt)).scalar_one()

        # Average OEE
        oee_scores = []
        for m in machines:
            oee_data = await calculate_machine_oee(db, m.machine_id, window_hours=24.0)
            oee_scores.append(oee_data.oee)
        plant_oee = round(sum(oee_scores) / len(oee_scores), 1) if oee_scores else 0.0

        # Average Health score approximation
        health_scores = [95.0 if m.current_status == "RUNNING" else (40.0 if m.current_status == "FAULT" else 75.0) for m in machines]
        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 100.0

        return PlantProductionSummary(
            total_machines=total,
            running_machines=running,
            stopped_machines=stopped,
            fault_machines=faults,
            maintenance_machines=maintenance,
            total_parts_produced=total_parts,
            active_alerts_count=int(active_alerts),
            average_plant_health=avg_health,
            plant_oee=plant_oee,
        )


machine_service = MachineService()
