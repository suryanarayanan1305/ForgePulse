"""
tests/test_health_score.py — Unit Tests for Transparent Machine Health Engine
"""

from app.services.health_score import calculate_machine_health


def test_nominal_operating_health():
    """Nominal machine operating within bounds should have high health score (>= 90)."""
    health = calculate_machine_health(
        temperature=50.0,
        temp_limit=85.0,
        vibration=1.5,
        vib_limit=7.5,
        pressure=6.0,
        pres_limit=10.0,
        status="RUNNING",
        error_code=None,
    )
    assert health.overall_health >= 90.0
    assert health.status_category == "HEALTHY"
    assert health.temperature_penalty == 0.0
    assert health.vibration_penalty == 0.0


def test_severe_overheating_health_penalty():
    """Overheating past thermal limit should apply significant penalty."""
    health = calculate_machine_health(
        temperature=95.0,
        temp_limit=85.0,
        vibration=1.5,
        vib_limit=7.5,
        pressure=6.0,
        pres_limit=10.0,
        status="RUNNING",
        error_code=None,
    )
    assert health.temperature_penalty > 20.0
    assert health.overall_health < 80.0


def test_critical_fault_and_error_penalties():
    """Combined mechanical vibration breach and error code should drop health into CRITICAL."""
    health = calculate_machine_health(
        temperature=88.0,
        temp_limit=85.0,
        vibration=11.2,  # severe vibration
        vib_limit=7.5,
        pressure=6.0,
        pres_limit=10.0,
        status="FAULT",
        error_code="E001",
    )
    assert health.overall_health < 50.0
    assert health.status_category == "CRITICAL"
    assert health.error_penalty == 20.0
    assert health.downtime_penalty == 20.0
