"""ORM Model: DowntimeLog — Machine downtime periods with computed duration"""
from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DowntimeLog(Base):
    __tablename__ = "downtime_logs"

    downtime_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    machine_id: Mapped[str] = mapped_column(String(50), ForeignKey("machines.machine_id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    reason_code: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # NOTE: duration_seconds is a GENERATED column in PostgreSQL (see schema.sql)
    # SQLAlchemy reads it as a regular column but never writes to it.
    # We store it mapped here for ORM access but PostgreSQL computes it automatically.
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    machine: Mapped["Machine"] = relationship("Machine", back_populates="downtime_logs")  # type: ignore[name-defined]

    @property
    def is_ongoing(self) -> bool:
        """True if the machine is currently in a downtime period."""
        return self.ended_at is None

    def __repr__(self) -> str:
        status = "ONGOING" if self.is_ongoing else f"{self.duration_seconds}s"
        return f"<DowntimeLog {self.machine_id} [{status}]>"
