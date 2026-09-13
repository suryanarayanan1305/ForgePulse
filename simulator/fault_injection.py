"""
simulator/fault_injection.py — Deterministic Fault Scenario Library
=====================================================================

PURPOSE:
  Provides named, reproducible fault scenarios for demonstrating
  the complete anomaly detection → alert → dashboard pipeline.

  Without fault injection, you would need to wait for random noise
  to occasionally exceed thresholds — unreliable in a live demo.

  With fault injection, you can say during an interview:
  "Watch — I'll inject an overheating fault on CNC-001 right now.
   Within 10 seconds you'll see the temperature chart spike,
   an alert appear in the dashboard, and the health score drop."

FAULT TYPES:
  OVERHEATING       — Simulates coolant system failure. Temperature climbs rapidly.
  HIGH_VIBRATION    — Simulates bearing wear or imbalance. Vibration spikes.
  PRESSURE_SPIKE    — Simulates blocked coolant line or hydraulic surge.
  MOTOR_OVERLOAD    — Simulates excessive cutting force or tool breakage.
  MACHINE_STOP      — Simulates unexpected E-stop or power loss.

IMPORTANT DISCLAIMER:
  These are simulated fault scenarios for demonstration purposes.
  This system does NOT control or monitor real industrial equipment.
  Do NOT use this for industrial safety-critical decisions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FaultScenario:
    """
    Defines a named fault scenario.

    intensity: 0.0 to 1.0
      0.3 = borderline — may or may not trigger warning threshold
      0.7 = clear anomaly — should trigger WARNING alert
      1.0 = severe — should trigger CRITICAL alert
    """
    fault_type: str
    display_name: str
    description: str
    intensity: float
    duration_seconds: Optional[int]  # None = persistent until cleared
    expected_alerts: list[str]       # For documentation/demo


# Predefined fault scenarios available via the API
FAULT_SCENARIOS: dict[str, FaultScenario] = {
    "OVERHEATING": FaultScenario(
        fault_type="OVERHEATING",
        display_name="Coolant System Failure (Overheating)",
        description=(
            "Simulates failure of the machine's coolant circulation system. "
            "Coolant flow drops to zero, causing spindle temperature to rise "
            "rapidly above the thermal limit. In a real machine, this would "
            "trigger an automatic emergency stop to prevent spindle seizure."
        ),
        intensity=0.75,
        duration_seconds=120,
        expected_alerts=["HIGH_TEMPERATURE", "PREDICTIVE_MAINTENANCE"],
    ),

    "HIGH_VIBRATION": FaultScenario(
        fault_type="HIGH_VIBRATION",
        display_name="Bearing Imbalance (Excessive Vibration)",
        description=(
            "Simulates progressive bearing wear or spindle imbalance. "
            "Vibration amplitude increases beyond the safe operating envelope. "
            "Prolonged high vibration causes accelerated bearing failure, "
            "reduced machining precision, and eventual catastrophic failure."
        ),
        intensity=0.80,
        duration_seconds=180,
        expected_alerts=["HIGH_VIBRATION", "PREDICTIVE_MAINTENANCE"],
    ),

    "PRESSURE_SPIKE": FaultScenario(
        fault_type="PRESSURE_SPIKE",
        display_name="Hydraulic Pressure Anomaly",
        description=(
            "Simulates a blocked coolant nozzle or hydraulic surge event. "
            "Pressure rises above the safe operating limit. "
            "For the hydraulic press, this represents a dangerous condition "
            "that could cause seal failure or pipe burst."
        ),
        intensity=0.65,
        duration_seconds=60,
        expected_alerts=["PRESSURE_ANOMALY"],
    ),

    "MOTOR_OVERLOAD": FaultScenario(
        fault_type="MOTOR_OVERLOAD",
        display_name="Motor Overload (Excessive Current Draw)",
        description=(
            "Simulates tool breakage or excessive cutting resistance causing "
            "the spindle motor to draw more current than rated. "
            "A real VFD (Variable Frequency Drive) would trip on overcurrent. "
            "Observable as excessive power consumption and rising temperature."
        ),
        intensity=0.70,
        duration_seconds=90,
        expected_alerts=["HIGH_POWER", "HIGH_TEMPERATURE", "PREDICTIVE_MAINTENANCE"],
    ),

    "MACHINE_STOP": FaultScenario(
        fault_type="MACHINE_STOP",
        display_name="Unexpected Machine Stop (E-Stop Simulation)",
        description=(
            "Simulates an unexpected emergency stop — operator pressed E-stop, "
            "power loss, or safety interlock triggered. "
            "Machine transitions immediately to FAULT state. "
            "Production count freezes and downtime clock starts."
        ),
        intensity=1.0,
        duration_seconds=None,  # Persistent — must be cleared manually
        expected_alerts=["UNEXPECTED_STOP", "DOWNTIME_STARTED"],
    ),

    # Compound fault: multiple metrics anomalous simultaneously
    "BEARING_FAULT": FaultScenario(
        fault_type="HIGH_VIBRATION",  # Reuses HIGH_VIBRATION with higher intensity
        display_name="Advanced Bearing Fault (Combined Anomaly)",
        description=(
            "Simulates an advanced bearing fault with multiple correlated anomalies: "
            "high vibration, slightly elevated temperature (bearing friction), "
            "and marginally increased power draw. "
            "This scenario is specifically designed to test multi-metric "
            "anomaly detection — no single metric crosses the threshold clearly, "
            "but the IsolationForest ML model detects the combined pattern."
        ),
        intensity=0.55,  # Each individual metric below clear threshold
        duration_seconds=300,
        expected_alerts=["HIGH_VIBRATION", "ANOMALY_DETECTED"],
    ),
}


class FaultInjector:
    """
    Manages fault injection state for the machine fleet.

    Tracks which machines have active faults and handles
    automatic fault expiry based on duration_seconds.
    """

    def __init__(self) -> None:
        # machine_id -> (FaultScenario, injected_at_timestamp, expires_at or None)
        self._active_faults: dict[str, tuple] = {}

    def inject(self, machine_id: str, fault_name: str, simulator) -> dict:
        """
        Injects a named fault into a machine simulator.

        Args:
            machine_id: Target machine identifier
            fault_name: Key from FAULT_SCENARIOS dict
            simulator: MachineSimulator instance for that machine

        Returns:
            dict with injection confirmation details
        """
        import time

        if fault_name not in FAULT_SCENARIOS:
            raise ValueError(
                f"Unknown fault: '{fault_name}'. "
                f"Available faults: {list(FAULT_SCENARIOS.keys())}"
            )

        scenario = FAULT_SCENARIOS[fault_name]
        simulator.inject_fault(scenario.fault_type, scenario.intensity)

        injected_at = time.time()
        expires_at = injected_at + scenario.duration_seconds if scenario.duration_seconds else None
        self._active_faults[machine_id] = (scenario, injected_at, expires_at)

        return {
            "machine_id": machine_id,
            "fault_name": fault_name,
            "fault_type": scenario.fault_type,
            "display_name": scenario.display_name,
            "intensity": scenario.intensity,
            "duration_seconds": scenario.duration_seconds,
            "expected_alerts": scenario.expected_alerts,
            "status": "INJECTED",
        }

    def clear(self, machine_id: str, simulator) -> dict:
        """
        Clears any active fault on a machine.

        Args:
            machine_id: Target machine identifier
            simulator: MachineSimulator instance for that machine
        """
        simulator.clear_fault()
        self._active_faults.pop(machine_id, None)
        return {"machine_id": machine_id, "status": "CLEARED"}

    def check_expirations(self, simulators: dict) -> list[str]:
        """
        Checks if any fault durations have expired and clears them.
        Called on every simulation tick.

        Returns:
            List of machine_ids whose faults were auto-cleared
        """
        import time

        cleared = []
        now = time.time()
        for machine_id, (scenario, injected_at, expires_at) in list(self._active_faults.items()):
            if expires_at is not None and now >= expires_at:
                if machine_id in simulators:
                    simulators[machine_id].clear_fault()
                del self._active_faults[machine_id]
                cleared.append(machine_id)
        return cleared

    def get_active_faults(self) -> dict:
        """Returns a summary of all currently active injected faults."""
        import time
        now = time.time()
        result = {}
        for machine_id, (scenario, injected_at, expires_at) in self._active_faults.items():
            elapsed = now - injected_at
            remaining = (expires_at - now) if expires_at else None
            result[machine_id] = {
                "fault_name": scenario.fault_type,
                "display_name": scenario.display_name,
                "intensity": scenario.intensity,
                "elapsed_seconds": round(elapsed, 1),
                "remaining_seconds": round(remaining, 1) if remaining else None,
            }
        return result

    def list_available_faults(self) -> list[dict]:
        """Returns all available fault scenarios for the dashboard fault injector UI."""
        return [
            {
                "fault_name": name,
                "display_name": scenario.display_name,
                "description": scenario.description,
                "intensity": scenario.intensity,
                "duration_seconds": scenario.duration_seconds,
                "expected_alerts": scenario.expected_alerts,
            }
            for name, scenario in FAULT_SCENARIOS.items()
        ]
