"""ORM Model: Alert — Alert lifecycle management with deduplication cooldown"""
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False)

    # Alert classification
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Triggering metric context
    metric_name: Mapped[str | None] = mapped_column(String(100))
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Alert lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Deduplication: prevents alert storms on persistent anomalies
    # While NOW() < cooldown_expires_at, we suppress same alert_type for same machine
    cooldown_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    machine: Mapped["Machine"] = relationship("Machine", back_populates="alerts")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type} [{self.severity}] on {self.machine_id}>"
