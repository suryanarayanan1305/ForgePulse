"""
schemas/telemetry.py — Pydantic Validation & Serialization Schemas for Telemetry
================================================================================
Defines strict input validation schemas for MQTT payload ingestion
and response models for REST API consumers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryBase(BaseModel):
    """Core telemetry attributes shared across ingestion and API models."""
    machine_id: str = Field(..., description="Unique machine identifier (e.g. CNC-001)", min_length=2, max_length=50)
    plant_id: str = Field(default="PLANT-A", description="Plant identifier")
    timestamp: datetime = Field(..., description="UTC ISO8601 reading timestamp")
    temperature: Optional[float] = Field(None, description="Spindle/oil temperature in °C", ge=-20.0, le=300.0)
    pressure: Optional[float] = Field(None, description="Coolant/hydraulic pressure in bar", ge=0.0, le=1000.0)
    vibration: Optional[float] = Field(None, description="RMS vibration in mm/s", ge=0.0, le=100.0)
    rpm: Optional[float] = Field(None, description="Rotational speed in RPM", ge=0.0, le=50000.0)
    power_consumption: Optional[float] = Field(None, description="Electrical power in kW", ge=0.0, le=1000.0)
    production_count: Optional[int] = Field(default=0, description="Cumulative parts count", ge=0)
    machine_status: Optional[str] = Field(default="STOPPED", description="RUNNING, STOPPED, MAINTENANCE, FAULT")
    error_code: Optional[str] = Field(default=None, description="Standard diagnostic trouble code or null")

    @field_validator("machine_id")
    @classmethod
    def normalize_machine_id(cls, v: str) -> str:
        return v.strip().upper()


class TelemetryIngest(TelemetryBase):
    """
    Schema for incoming raw MQTT telemetry payloads.
    Includes optional PLC diagnostic metadata.
    """
    plc_meta: Optional[Dict[str, Any]] = Field(default=None, alias="_plc_meta", description="Simulated PLC diagnostic data")
    model_config = ConfigDict(populate_by_name=True)


class TelemetryResponse(TelemetryBase):
    """API response model for persisted telemetry records."""
    telemetry_id: UUID
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetrySummary(BaseModel):
    """Aggregated telemetry statistical summary for a machine."""
    machine_id: str
    sample_count: int
    avg_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    avg_vibration: Optional[float] = None
    max_vibration: Optional[float] = None
    avg_pressure: Optional[float] = None
    max_power: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
