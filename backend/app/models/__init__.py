"""Package init — exports all models so Alembic can auto-discover them."""
from app.models.plant import Plant
from app.models.machine import Machine
from app.models.sensor import MachineSensor
from app.models.telemetry import Telemetry
from app.models.event import MachineEvent
from app.models.alert import Alert
from app.models.downtime import DowntimeLog
from app.models.maintenance import MaintenanceRecord

__all__ = [
    "Plant", "Machine", "MachineSensor", "Telemetry",
    "MachineEvent", "Alert", "DowntimeLog", "MaintenanceRecord",
]
