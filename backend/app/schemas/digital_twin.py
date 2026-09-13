"""
schemas/digital_twin.py — Comprehensive Digital Twin Representation Schema
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.telemetry import TelemetryResponse
from app.schemas.alert import AlertResponse


class MachineIdentity(BaseModel):
    machine_id: str
    machine_name: str
    machine_type: str
    plant_id: str
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    rated_rpm: Optional[float] = None
    temperature_limit: float
    vibration_limit: float
    pressure_limit: float
    power_limit: Optional[float] = None


class HealthBreakdown(BaseModel):
    overall_health: float = Field(..., description="Calculated health score between 0 and 100")
    status_category: str = Field(..., description="HEALTHY, WARNING, CRITICAL, OFFLINE")
    temperature_penalty: float = 0.0
    vibration_penalty: float = 0.0
    pressure_penalty: float = 0.0
    error_penalty: float = 0.0
    downtime_penalty: float = 0.0
    formula_explanation: str


class PredictiveMaintenanceInsight(BaseModel):
    risk_score: float = Field(..., description="Estimated failure risk 0 to 100%")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    signals: List[str] = []
    recommendation: str
    disclaimer: str = "Prototype maintenance-risk estimation only. Not for real industrial safety."


class ProductionSummary(BaseModel):
    total_parts: int = 0
    operating_hours: float = 0.0
    downtime_minutes: float = 0.0
    current_run_duration_minutes: float = 0.0


class DigitalTwinResponse(BaseModel):
    """Unified Digital Twin payload combining static metadata, dynamic telemetry, and analytical models."""
    identity: MachineIdentity
    current_status: str
    health: HealthBreakdown
    maintenance_prediction: PredictiveMaintenanceInsight
    production: ProductionSummary
    latest_telemetry: Optional[TelemetryResponse] = None
    active_alerts: List[AlertResponse] = []
    last_seen: Optional[datetime] = None
    twin_timestamp: datetime
