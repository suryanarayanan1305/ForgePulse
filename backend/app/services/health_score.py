"""
services/health_score.py — Transparent Machine Health Score Calculation Engine
================================================================================

TRANSPARENT FORMULA:
  Health = 100 - (Temperature_Penalty + Vibration_Penalty + Pressure_Penalty + Error_Penalty + Downtime_Penalty)
  Score is clamped strictly to [0.0, 100.0].

WEIGHTED PENALTIES:
  - Temperature: Up to 30 points if approaching or exceeding limit.
  - Vibration:   Up to 35 points (bearing/mechanical integrity is primary failure indicator).
  - Pressure:    Up to 15 points.
  - Error Codes: 20 points if active diagnostic error code present.
  - Downtime:    10 points if currently stopped or in fault.

CATEGORIZATION:
  - 85 - 100: HEALTHY (Green)
  - 60 - 84:  WARNING (Yellow)
  - 0  - 59:  CRITICAL (Red)
"""

from typing import Optional
from app.schemas.digital_twin import HealthBreakdown


def calculate_machine_health(
    temperature: Optional[float],
    temp_limit: float,
    vibration: Optional[float],
    vib_limit: float,
    pressure: Optional[float],
    pres_limit: float,
    status: str,
    error_code: Optional[str] = None,
) -> HealthBreakdown:
    """
    Computes deterministic machine health with a full penalty breakdown.
    """
    temp_penalty = 0.0
    vib_penalty = 0.0
    pres_penalty = 0.0
    error_penalty = 0.0
    downtime_penalty = 0.0

    # 1. Temperature Penalty (Weight: 30)
    if temperature is not None and temp_limit > 0:
        ratio = temperature / temp_limit
        if ratio > 1.0:
            temp_penalty = min(30.0, 20.0 + (ratio - 1.0) * 50.0)
        elif ratio > 0.85:
            temp_penalty = (ratio - 0.85) / 0.15 * 15.0

    # 2. Vibration Penalty (Weight: 35 - critical mechanical health)
    if vibration is not None and vib_limit > 0:
        ratio = vibration / vib_limit
        if ratio > 1.0:
            vib_penalty = min(35.0, 25.0 + (ratio - 1.0) * 50.0)
        elif ratio > 0.75:
            vib_penalty = (ratio - 0.75) / 0.25 * 20.0

    # 3. Pressure Penalty (Weight: 15)
    if pressure is not None and pres_limit > 0:
        ratio = pressure / pres_limit
        if ratio > 1.0:
            pres_penalty = min(15.0, 10.0 + (ratio - 1.0) * 25.0)
        elif ratio > 0.9:
            pres_penalty = (ratio - 0.9) / 0.1 * 8.0

    # 4. Error Code Penalty (Weight: 20)
    if error_code:
        error_penalty = 20.0

    # 5. Downtime Penalty (Weight: 10)
    if status == "FAULT":
        downtime_penalty = 20.0
    elif status == "STOPPED":
        downtime_penalty = 5.0

    total_penalties = temp_penalty + vib_penalty + pres_penalty + error_penalty + downtime_penalty
    overall_health = max(0.0, min(100.0, 100.0 - total_penalties))

    if status in ("FAULT",) or overall_health < 60.0:
        category = "CRITICAL"
    elif status in ("MAINTENANCE",) or overall_health < 85.0:
        category = "WARNING"
    else:
        category = "HEALTHY"

    explanation = (
        f"Health: {overall_health:.1f}/100 [Base: 100 - Penalties: "
        f"Temp={temp_penalty:.1f}, Vib={vib_penalty:.1f}, Pres={pres_penalty:.1f}, "
        f"Err={error_penalty:.1f}, Down={downtime_penalty:.1f}]"
    )

    return HealthBreakdown(
        overall_health=round(overall_health, 1),
        status_category=category,
        temperature_penalty=round(temp_penalty, 1),
        vibration_penalty=round(vib_penalty, 1),
        pressure_penalty=round(pres_penalty, 1),
        error_penalty=round(error_penalty, 1),
        downtime_penalty=round(downtime_penalty, 1),
        formula_explanation=explanation,
    )
