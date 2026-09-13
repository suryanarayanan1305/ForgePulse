"""
schemas/alert.py — Alert Engine Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    machine_id: str
    alert_type: str
    severity: str = Field(..., description="INFO, WARNING, CRITICAL")
    message: str
    metric_name: Optional[str] = None
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertCreate(AlertBase):
    cooldown_expires_at: Optional[datetime] = None


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., description="Operator name or ID")


class AlertResponse(AlertBase):
    alert_id: UUID
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
