"""ORM Model: Machine — Physical (Simulated) Shop Floor Asset"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.plant import Plant
    from app.models.telemetry import Telemetry
    from app.models.alert import Alert
    from app.models.downtime import DowntimeLog
    from app.models.maintenance import MaintenanceRecord
    from app.models.event import MachineEvent
    from app.models.sensor import MachineSensor


class Machine(Base):
    __tablename__ = "machines"

    machine_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    machine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(100), nullable=False)
    plant_id: Mapped[str] = mapped_column(String(50), ForeignKey("plants.plant_id"), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(200))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    installation_date: Mapped[date | None] = mapped_column(Date)

    # Operating limits — used by anomaly detection and health score engine
    rated_rpm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    temperature_limit: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=85.0)
    vibration_limit: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=8.0)
    pressure_limit: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=12.0)
    power_limit: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    # Current operational state — updated by MQTT ingestion worker
    current_status: Mapped[str] = mapped_column(String(50), nullable=False, default="STOPPED")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="machines")
    sensors: Mapped[List["MachineSensor"]] = relationship("MachineSensor", back_populates="machine", lazy="select")
    telemetry: Mapped[List["Telemetry"]] = relationship("Telemetry", back_populates="machine", lazy="select")
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="machine", lazy="select")
    downtime_logs: Mapped[List["DowntimeLog"]] = relationship("DowntimeLog", back_populates="machine", lazy="select")
    maintenance_records: Mapped[List["MaintenanceRecord"]] = relationship("MaintenanceRecord", back_populates="machine", lazy="select")
    events: Mapped[List["MachineEvent"]] = relationship("MachineEvent", back_populates="machine", lazy="select")

    def __repr__(self) -> str:
        return f"<Machine {self.machine_id} [{self.current_status}]>"
