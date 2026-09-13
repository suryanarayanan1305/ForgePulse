"""
schemas/machine.py — Machine Schemas
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MachineSensorResponse(BaseModel):
    sensor_type: str
    sensor_name: str
    unit: str
    min_normal: Optional[float] = None
    max_normal: Optional[float] = None
    critical_limit: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class MachineBase(BaseModel):
    machine_id: str
    machine_name: str
    machine_type: str
    plant_id: str
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    rated_rpm: Optional[float] = None
    temperature_limit: float = 85.0
    vibration_limit: float = 8.0
    pressure_limit: float = 12.0
    power_limit: Optional[float] = None


class MachineResponse(MachineBase):
    current_status: str
    last_seen_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MachineDetailResponse(MachineResponse):
    sensors: List[MachineSensorResponse] = []

    model_config = ConfigDict(from_attributes=True)
