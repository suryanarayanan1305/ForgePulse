"""
tests/conftest.py — Pytest Configuration & Test Fixtures
"""

import sys
import os
import pytest

# Ensure backend directory is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.schemas.telemetry import TelemetryIngest
from datetime import datetime, timezone


@pytest.fixture
def sample_telemetry_payload() -> dict:
    return {
        "machine_id": "CNC-001",
        "plant_id": "PLANT-A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 72.5,
        "pressure": 6.8,
        "vibration": 1.85,
        "rpm": 5500.0,
        "power_consumption": 14.2,
        "production_count": 120,
        "machine_status": "RUNNING",
        "error_code": None,
    }


@pytest.fixture
def anomalous_telemetry_payload() -> dict:
    return {
        "machine_id": "CNC-001",
        "plant_id": "PLANT-A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 94.2,  # Breaches 85.0°C limit
        "pressure": 6.8,
        "vibration": 9.4,   # Breaches 7.5 mm/s limit
        "rpm": 5500.0,
        "power_consumption": 26.5,  # Breaches 22.0 kW limit
        "production_count": 125,
        "machine_status": "RUNNING",
        "error_code": "E002",
    }
