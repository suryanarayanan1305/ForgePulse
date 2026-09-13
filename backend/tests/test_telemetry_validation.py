"""
tests/test_telemetry_validation.py — Unit Tests for Telemetry Pydantic Validation
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from app.schemas.telemetry import TelemetryIngest


def test_valid_telemetry_ingest(sample_telemetry_payload):
    """Valid payload should parse cleanly and normalize machine_id."""
    model = TelemetryIngest.model_validate(sample_telemetry_payload)
    assert model.machine_id == "CNC-001"
    assert model.temperature == 72.5
    assert model.rpm == 5500.0


def test_lowercase_machine_id_normalization():
    """Lowercase machine ID should be uppercase normalized."""
    payload = {
        "machine_id": " cnc-002 ",
        "plant_id": "PLANT-A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 60.0,
    }
    model = TelemetryIngest.model_validate(payload)
    assert model.machine_id == "CNC-002"


def test_invalid_telemetry_out_of_bounds():
    """Values physically out of bounds must fail Pydantic validation."""
    invalid_payload = {
        "machine_id": "CNC-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 1500.0,  # Exceeds max allowed 300°C
    }
    with pytest.raises(ValidationError):
        TelemetryIngest.model_validate(invalid_payload)
