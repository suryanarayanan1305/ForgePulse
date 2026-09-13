"""ORM Model: Telemetry — Periodic machine sensor readings (highest-volume table)"""
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False)
    plant_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Core sensor readings — separate relational columns (NOT JSON) for SQL analytics
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))     # °C
    pressure: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))        # bar
    vibration: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))       # mm/s RMS
    rpm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))             # RPM
    power_consumption: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))  # kW
    production_count: Mapped[int | None] = mapped_column(Integer, default=0)
    machine_status: Mapped[str | None] = mapped_column(String(50))
    error_code: Mapped[str | None] = mapped_column(String(50))

    # Anomaly detection results — set by backend ingestion worker
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    machine: Mapped["Machine"] = relationship("Machine", back_populates="telemetry")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Telemetry {self.machine_id} @ {self.timestamp}>"
