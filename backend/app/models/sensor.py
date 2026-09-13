"""ORM Model: MachineSensor — Per-sensor specifications"""
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MachineSensor(Base):
    __tablename__ = "machine_sensors"

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    min_normal: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    max_normal: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    critical_limit: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    machine: Mapped["Machine"] = relationship("Machine", back_populates="sensors")  # type: ignore[name-defined]
