"""ORM Model: Plant — Manufacturing Facility / Site"""
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.machine import Machine


class Plant(Base):
    __tablename__ = "plants"

    plant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    plant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship: one plant → many machines
    machines: Mapped[List["Machine"]] = relationship("Machine", back_populates="plant", lazy="select")

    def __repr__(self) -> str:
        return f"<Plant {self.plant_id}: {self.plant_name}>"
