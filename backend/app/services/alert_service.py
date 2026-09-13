"""
services/alert_service.py — Alert Engine with Cooldown Deduplication
====================================================================

PURPOSE:
  Evaluates anomaly conditions and raises alerts while preventing "alert spam".
  Implements a rolling cooldown window (`cooldown_expires_at`).
  If the same alert type is detected on the same machine during an active cooldown window,
  the repeated alert is suppressed to prevent overwhelming operators and logs.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.alert import Alert
from app.schemas.alert import AlertResponse

logger = logging.getLogger(__name__)


class AlertService:
    """
    Manages creation, deduplication, queries, and acknowledgments for machine alerts.
    """

    async def raise_alert_if_not_suppressed(
        self,
        db: AsyncSession,
        machine_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metric_name: Optional[str] = None,
        observed_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
    ) -> Optional[Alert]:
        """
        Creates an alert if no active unexpired alert of the same type exists for this machine.
        """
        settings = get_settings()
        now = datetime.now(timezone.utc)

        # Check for active cooldown
        stmt = (
            select(Alert)
            .where(
                and_(
                    Alert.machine_id == machine_id,
                    Alert.alert_type == alert_type,
                    Alert.status == "OPEN",
                    Alert.cooldown_expires_at > now,
                )
            )
            .order_by(desc(Alert.timestamp))
            .limit(1)
        )
        existing_alert = (await db.execute(stmt)).scalar_one_or_none()

        if existing_alert:
            logger.debug(f"Suppressed duplicate alert: {alert_type} on {machine_id} (cooldown active)")
            return None

        cooldown_expiry = now + timedelta(seconds=settings.ALERT_COOLDOWN_SECONDS)
        new_alert = Alert(
            machine_id=machine_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_name=metric_name,
            observed_value=observed_value,
            threshold_value=threshold_value,
            status="OPEN",
            cooldown_expires_at=cooldown_expiry,
            timestamp=now,
        )
        db.add(new_alert)
        await db.flush()
        logger.warning(f"ALERT CREATED: [{severity}] {alert_type} on {machine_id}: {message}")
        return new_alert

    async def get_active_alerts(
        self,
        db: AsyncSession,
        machine_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """Fetches active/open alerts."""
        stmt = select(Alert).where(Alert.status == "OPEN").order_by(desc(Alert.timestamp)).limit(limit)
        if machine_id:
            stmt = stmt.where(Alert.machine_id == machine_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def acknowledge_alert(
        self,
        db: AsyncSession,
        alert_id: UUID,
        acknowledged_by: str,
    ) -> Optional[Alert]:
        """Marks an alert as ACKNOWLEDGED."""
        now = datetime.now(timezone.utc)
        stmt = select(Alert).where(Alert.alert_id == alert_id)
        alert = (await db.execute(stmt)).scalar_one_or_none()
        if not alert:
            return None

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = now
        alert.acknowledged_by = acknowledged_by
        await db.flush()
        return alert

    async def resolve_alert(
        self,
        db: AsyncSession,
        alert_id: UUID,
    ) -> Optional[Alert]:
        """Marks an alert as RESOLVED."""
        now = datetime.now(timezone.utc)
        stmt = select(Alert).where(Alert.alert_id == alert_id)
        alert = (await db.execute(stmt)).scalar_one_or_none()
        if not alert:
            return None

        alert.status = "RESOLVED"
        alert.resolved_at = now
        await db.flush()
        return alert


alert_service = AlertService()
