"""
schemas/analytics.py — Production & Quality Analytics Schemas (OEE, Downtime, Trends)
"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OEEMetrics(BaseModel):
    """Overall Equipment Effectiveness components."""
    availability: float = Field(..., description="Operating Time / Planned Production Time (0-100%)")
    performance: float = Field(..., description="Actual Speed / Ideal Rated Speed (0-100%)")
    quality: float = Field(..., description="Good Parts / Total Parts (0-100%)")
    oee: float = Field(..., description="Availability * Performance * Quality (0-100%)")
    planned_production_minutes: float
    operating_minutes: float
    downtime_minutes: float
    total_production_count: int
    scrap_count: int = 0
    disclaimer: str = "Demonstrative OEE calculation based on simulated shop floor telemetry."


class PlantProductionSummary(BaseModel):
    total_machines: int
    running_machines: int
    stopped_machines: int
    fault_machines: int
    maintenance_machines: int
    total_parts_produced: int
    active_alerts_count: int
    average_plant_health: float
    plant_oee: float


class DowntimeSummary(BaseModel):
    machine_id: str
    total_downtime_minutes: float
    event_count: int
    primary_reason: Optional[str] = None
    last_downtime_start: Optional[datetime] = None


class TrendPoint(BaseModel):
    timestamp: datetime
    value: float
    is_anomaly: bool = False


class MetricTrendResponse(BaseModel):
    machine_id: str
    metric_name: str
    unit: str
    limit_value: float
    data_points: List[TrendPoint] = []
