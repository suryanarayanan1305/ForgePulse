"""
analytics/downtime.py — Machine State Transition & Downtime Tracking Engine
=============================================================================
Monitors machine operational states (RUNNING ↔ STOPPED ↔ FAULT ↔ MAINTENANCE)
and records discrete downtime events with reason codes and durations.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import logging
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.downtime import DowntimeLog
from app.models.machine import Machine

logger = logging.getLogger(__name__)


class DowntimeTracker:
    """
    Manages live state machine tracking per machine.
    Detects state transitions and manages open/closed downtime log records in PostgreSQL.
    """

    def __init__(self) -> None:
        # Cache of previous known status: machine_id -> status string
        self._last_known_status: Dict[str, str] = {}

    async def handle_status_transition(
        self,
        db: AsyncSession,
        machine_id: str,
        new_status: str,
        timestamp: datetime,
        error_code: Optional[str] = None,
    ) -> Optional[DowntimeLog]:
        """
        Evaluates machine state changes.
        - If RUNNING -> STOPPED/FAULT/MAINTENANCE: Creates a new open DowntimeLog record.
        - If STOPPED/FAULT/MAINTENANCE -> RUNNING: Closes existing open DowntimeLog record.
        """
        prev_status = self._last_known_status.get(machine_id)
        self._last_known_status[machine_id] = new_status

        if prev_status is None:
            # First observation: if already down, check if open record exists
            if new_status in ("STOPPED", "FAULT", "MAINTENANCE"):
                open_log = await self._get_open_downtime(db, machine_id)
                if not open_log:
                    return await self._create_downtime_record(db, machine_id, new_status, timestamp, error_code)
            return None

        # State Transition: Became Down
        if prev_status == "RUNNING" and new_status in ("STOPPED", "FAULT", "MAINTENANCE"):
            logger.info(f"Machine {machine_id} transitioned: {prev_status} -> {new_status} (Downtime started)")
            return await self._create_downtime_record(db, machine_id, new_status, timestamp, error_code)

        # State Transition: Recovered / Resumed Running
        elif prev_status in ("STOPPED", "FAULT", "MAINTENANCE") and new_status == "RUNNING":
            logger.info(f"Machine {machine_id} transitioned: {prev_status} -> RUNNING (Downtime ended)")
            await self._close_open_downtime(db, machine_id, timestamp)
            return None

        return None

    async def _get_open_downtime(self, db: AsyncSession, machine_id: str) -> Optional[DowntimeLog]:
        stmt = select(DowntimeLog).where(
            and_(DowntimeLog.machine_id == machine_id, DowntimeLog.ended_at.is_(None))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_downtime_record(
        self,
        db: AsyncSession,
        machine_id: str,
        status: str,
        started_at: datetime,
        error_code: Optional[str],
    ) -> DowntimeLog:
        reason = "UNPLANNED_FAULT" if status == "FAULT" else ("SCHEDULED_MAINTENANCE" if status == "MAINTENANCE" else "STOPPED_CYCLE")
        log = DowntimeLog(
            machine_id=machine_id,
            reason=reason,
            reason_code=error_code or status,
            started_at=started_at,
            ended_at=None,
        )
        db.add(log)
        await db.flush()
        return log

    async def _close_open_downtime(self, db: AsyncSession, machine_id: str, ended_at: datetime) -> None:
        stmt = (
            update(DowntimeLog)
            .where(and_(DowntimeLog.machine_id == machine_id, DowntimeLog.ended_at.is_(None)))
            .values(ended_at=ended_at)
        )
        await db.execute(stmt)
        await db.flush()


# Module-level singleton
downtime_tracker = DowntimeTracker()
