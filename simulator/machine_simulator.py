"""
simulator/machine_simulator.py — Physics-Inspired Machine State Engine
========================================================================

WHAT THIS IS:
  A software simulation of 5 industrial machines (CNC machining centers,
  a hydraulic press, and a milling machine). Each machine has an internal
  physics state that evolves realistically over time.

WHY NOT RANDOM VALUES?
  Using random.uniform(20, 85) for temperature would be useless for
  anomaly detection — every reading would look "anomalous" or the detector
  would learn to ignore them. Real machines follow physical laws:

  - Temperature rises as RPM increases (friction → heat)
  - Temperature falls slowly when machine stops (thermal dissipation)
  - Vibration correlates with RPM but spikes during bearing faults
  - Power consumption scales with mechanical load
  - Production count increments only while machine is RUNNING

PHYSICAL MODEL USED (simplified):
  Thermal: T[t+1] = T[t] + (RPM_ratio * heat_rate) - (cooling_coeff * (T[t] - T_ambient))
  Vibration: V = V_base * (0.7 + 0.3 * RPM_ratio) + gaussian_noise + fault_offset
  Power: P = P_idle + (P_max - P_idle) * RPM_ratio * load_factor + noise

  This is NOT a real industrial thermal model — it's a simplified approximation
  sufficient for demonstrating anomaly detection behavior.

INTERVIEW ANSWER:
  "I used a simplified first-order thermal model to make temperature
  correlate with RPM. This is not a CFD simulation — it's a behavioral
  model sufficient to generate realistic normal and anomalous patterns
  for demonstrating the detection pipeline."
"""

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MachineStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    MAINTENANCE = "MAINTENANCE"
    FAULT = "FAULT"


@dataclass
class MachineConfig:
    """Static configuration for a simulated machine."""
    machine_id: str
    machine_name: str
    machine_type: str           # CNC, PRESS, MILL
    plant_id: str
    rated_rpm: float            # Maximum operating RPM
    temperature_limit: float    # °C — triggers alert above this
    vibration_limit: float      # mm/s RMS — triggers alert above this
    pressure_limit: float       # bar — triggers alert above this
    power_limit: float          # kW
    ambient_temperature: float = 28.0  # °C (Chennai factory floor)

    # Physics model parameters
    heat_generation_rate: float = 0.08   # °C per second at full RPM
    cooling_coefficient: float = 0.015   # Heat dissipation rate
    vibration_base: float = 1.2          # mm/s at idle
    pressure_nominal: float = 6.0        # bar (operating pressure)
    power_idle: float = 2.0              # kW at idle/stopped


@dataclass
class MachinePhysicsState:
    """
    Dynamic state of a machine — changes every simulation tick.

    This is the "internal state" that the PLC reads.
    Different from the telemetry payload (which is the formatted outgoing message).
    """
    # Operating state
    status: MachineStatus = MachineStatus.STOPPED
    current_rpm: float = 0.0
    target_rpm: float = 0.0         # RPM the machine is ramping toward

    # Sensor readings (current values)
    temperature: float = 28.0       # °C
    pressure: float = 1.0           # bar
    vibration: float = 0.1          # mm/s RMS
    power_consumption: float = 0.5  # kW
    production_count: int = 0
    error_code: Optional[str] = None

    # Fault injection state
    fault_active: bool = False
    fault_type: Optional[str] = None
    fault_intensity: float = 0.0    # 0.0 to 1.0 — how severe is the injected fault

    # Internal tracking
    session_production: int = 0     # Parts since last startup
    uptime_seconds: float = 0.0

    # Ramp parameters — machines don't instantly change RPM
    rpm_ramp_rate: float = 100.0    # RPM per second (acceleration)


# Machine fleet configuration — realistic specs
MACHINE_FLEET: list[MachineConfig] = [
    MachineConfig(
        machine_id="CNC-001",
        machine_name="CNC Machining Center Alpha",
        machine_type="CNC",
        plant_id="PLANT-A",
        rated_rpm=8000.0,
        temperature_limit=85.0,
        vibration_limit=7.5,
        pressure_limit=10.0,
        power_limit=22.0,
        heat_generation_rate=0.09,
        cooling_coefficient=0.012,
        vibration_base=1.0,
        pressure_nominal=6.5,
        power_idle=2.5,
    ),
    MachineConfig(
        machine_id="CNC-002",
        machine_name="CNC Machining Center Beta",
        machine_type="CNC",
        plant_id="PLANT-A",
        rated_rpm=6000.0,
        temperature_limit=82.0,
        vibration_limit=7.0,
        pressure_limit=10.0,
        power_limit=30.0,
        heat_generation_rate=0.10,
        cooling_coefficient=0.011,
        vibration_base=1.1,
        pressure_nominal=6.0,
        power_idle=3.0,
    ),
    MachineConfig(
        machine_id="CNC-003",
        machine_name="CNC Machining Center Gamma",
        machine_type="CNC",
        plant_id="PLANT-A",
        rated_rpm=6000.0,
        temperature_limit=80.0,
        vibration_limit=7.0,
        pressure_limit=9.5,
        power_limit=25.0,
        heat_generation_rate=0.085,
        cooling_coefficient=0.013,
        vibration_base=1.3,    # Slightly higher baseline — older machine
        pressure_nominal=5.8,
        power_idle=2.2,
    ),
    MachineConfig(
        machine_id="PRESS-001",
        machine_name="Hydraulic Press Station 1",
        machine_type="PRESS",
        plant_id="PLANT-A",
        rated_rpm=300.0,
        temperature_limit=70.0,    # Hydraulic oil temperature
        vibration_limit=5.0,
        pressure_limit=250.0,      # Hydraulic pressure (much higher!)
        power_limit=75.0,
        heat_generation_rate=0.05,
        cooling_coefficient=0.008,
        vibration_base=0.8,
        pressure_nominal=180.0,    # Hydraulic operating pressure
        power_idle=5.0,
    ),
    MachineConfig(
        machine_id="MILL-001",
        machine_name="Vertical Milling Machine 1",
        machine_type="MILL",
        plant_id="PLANT-A",
        rated_rpm=4000.0,
        temperature_limit=75.0,
        vibration_limit=6.5,
        pressure_limit=8.0,
        power_limit=15.0,
        heat_generation_rate=0.07,
        cooling_coefficient=0.014,
        vibration_base=0.9,
        pressure_nominal=5.0,
        power_idle=1.8,
    ),
]


class MachineSimulator:
    """
    Simulates the physics state of a single machine.

    Each machine is an independent object — they evolve in parallel.
    The main simulator loop calls tick() on every machine every N seconds.

    The PLC reads from state (MachinePhysicsState) every scan cycle.
    """

    def __init__(self, config: MachineConfig) -> None:
        self.config = config
        self.state = MachinePhysicsState(
            temperature=config.ambient_temperature + random.uniform(0, 3)
        )
        self._tick_count = 0

    def start(self, target_rpm: Optional[float] = None) -> None:
        """Command: start the machine at a given RPM (or rated RPM)."""
        if self.state.status in (MachineStatus.FAULT,):
            return  # Cannot start while in fault state
        self.state.status = MachineStatus.RUNNING
        self.state.target_rpm = target_rpm or (self.config.rated_rpm * random.uniform(0.6, 0.9))
        self.state.error_code = None
        self.state.session_production = 0

    def stop(self, reason: str = "PLANNED") -> None:
        """Command: stop the machine."""
        self.state.status = MachineStatus.STOPPED
        self.state.target_rpm = 0.0
        self.state.error_code = None

    def set_maintenance(self) -> None:
        """Command: put the machine in maintenance mode."""
        self.state.status = MachineStatus.MAINTENANCE
        self.state.target_rpm = 0.0

    def inject_fault(self, fault_type: str, intensity: float = 0.7) -> None:
        """
        Inject a deterministic fault scenario.
        The fault alters the physics state to produce anomalous telemetry.

        fault_type options (defined in fault_injection.py):
          OVERHEATING, HIGH_VIBRATION, PRESSURE_SPIKE, MOTOR_OVERLOAD, MACHINE_STOP

        intensity: 0.0 to 1.0 — how severe the fault is
          0.3 = borderline warning
          0.7 = clear anomaly
          1.0 = critical fault
        """
        self.state.fault_active = True
        self.state.fault_type = fault_type
        self.state.fault_intensity = max(0.0, min(1.0, intensity))

        if fault_type == "MACHINE_STOP":
            # Simulates unexpected stop (e.g., E-stop pressed, power loss)
            self.state.status = MachineStatus.FAULT
            self.state.target_rpm = 0.0
            self.state.error_code = "E001"

    def clear_fault(self) -> None:
        """Clear the injected fault and return to normal behavior."""
        self.state.fault_active = False
        self.state.fault_type = None
        self.state.fault_intensity = 0.0
        self.state.error_code = None
        if self.state.status == MachineStatus.FAULT:
            self.state.status = MachineStatus.STOPPED

    def tick(self, dt: float = 2.0) -> None:
        """
        Advance the machine physics state by dt seconds.

        Called by the main simulator loop on every publish interval.

        Physics applied:
          1. RPM ramps toward target (not instant — simulates motor inertia)
          2. Temperature evolves based on RPM load and cooling
          3. Vibration set based on RPM + noise + fault offset
          4. Pressure varies around nominal with small fluctuation
          5. Power consumption scales with RPM load
          6. Production count increments while RUNNING

        Args:
            dt: Time delta in seconds since last tick
        """
        self._tick_count += 1
        s = self.state
        c = self.config

        # --- 1. RPM Ramp (simulates motor inertia) ---
        rpm_gap = s.target_rpm - s.current_rpm
        max_change = s.rpm_ramp_rate * dt
        if abs(rpm_gap) <= max_change:
            s.current_rpm = s.target_rpm
        else:
            s.current_rpm += max_change * (1 if rpm_gap > 0 else -1)
        s.current_rpm = max(0.0, s.current_rpm)

        # RPM ratio: 0.0 = stopped, 1.0 = full rated speed
        rpm_ratio = s.current_rpm / c.rated_rpm if c.rated_rpm > 0 else 0.0
        rpm_ratio = max(0.0, min(1.0, rpm_ratio))

        # --- 2. Thermal Model ---
        # Heat in: proportional to RPM (friction)
        # Heat out: proportional to temperature above ambient (dissipation/cooling)
        if s.status == MachineStatus.RUNNING:
            heat_in = c.heat_generation_rate * rpm_ratio * dt
        else:
            heat_in = 0.0

        heat_out = c.cooling_coefficient * (s.temperature - c.ambient_temperature) * dt
        delta_T = heat_in - heat_out
        s.temperature += delta_T

        # Fault override: OVERHEATING reduces cooling (simulates coolant failure)
        if s.fault_active and s.fault_type == "OVERHEATING":
            extra_heat = c.heat_generation_rate * s.fault_intensity * 2.5 * dt
            s.temperature += extra_heat

        # Keep temperature physically plausible (can't go below ambient)
        s.temperature = max(c.ambient_temperature, s.temperature)

        # Add realistic sensor noise (±0.3°C)
        s.temperature += random.gauss(0, 0.15)

        # --- 3. Vibration Model ---
        if s.status == MachineStatus.RUNNING:
            # Base vibration scales with RPM (higher speed = more vibration)
            v_base = c.vibration_base * (0.5 + 0.5 * rpm_ratio)
        else:
            v_base = c.vibration_base * 0.1  # Residual vibration when stopped

        # Fault override: BEARING_FAULT or HIGH_VIBRATION
        fault_v_offset = 0.0
        if s.fault_active and s.fault_type in ("HIGH_VIBRATION", "BEARING_FAULT"):
            # Vibration can jump significantly above limit with bearing fault
            fault_v_offset = (c.vibration_limit * 0.5 + c.vibration_limit * s.fault_intensity * 1.2)

        # Sensor noise (vibration is noisier than temperature)
        v_noise = random.gauss(0, v_base * 0.08)
        s.vibration = max(0.0, v_base + fault_v_offset + v_noise)

        # --- 4. Pressure Model ---
        if s.status == MachineStatus.RUNNING:
            p_target = c.pressure_nominal * (0.85 + 0.15 * rpm_ratio)
        else:
            # Residual pressure when stopped (hydraulic systems retain pressure)
            p_target = c.pressure_nominal * 0.3 if c.machine_type == "PRESS" else 1.0

        # Fault override: PRESSURE_SPIKE
        p_fault_offset = 0.0
        if s.fault_active and s.fault_type == "PRESSURE_SPIKE":
            p_fault_offset = c.pressure_limit * 0.3 * s.fault_intensity

        p_noise = random.gauss(0, p_target * 0.015)
        s.pressure = max(0.0, p_target + p_fault_offset + p_noise)

        # --- 5. Power Consumption Model ---
        if s.status == MachineStatus.RUNNING:
            p_mechanical = (c.power_limit - c.power_idle) * rpm_ratio
            # Motor overload: draws more power than rated
            if s.fault_active and s.fault_type == "MOTOR_OVERLOAD":
                p_mechanical *= (1.0 + 0.4 * s.fault_intensity)
            p_noise = random.gauss(0, p_mechanical * 0.03)
            s.power_consumption = c.power_idle + p_mechanical + p_noise
        else:
            # Standby power draw (PLC, controls, lighting)
            s.power_consumption = c.power_idle * 0.4 + random.gauss(0, 0.1)

        s.power_consumption = max(0.0, s.power_consumption)

        # --- 6. Production Count ---
        if s.status == MachineStatus.RUNNING and s.current_rpm > c.rated_rpm * 0.3:
            # Probabilistic part production — not every tick produces a part
            # CNC machines produce roughly 1 part per 30-120 seconds
            production_probability = rpm_ratio * dt / 45.0
            if random.random() < production_probability:
                s.production_count += 1
                s.session_production += 1

        # --- 7. Uptime tracking ---
        if s.status == MachineStatus.RUNNING:
            s.uptime_seconds += dt

        # --- 8. Spontaneous state changes (realistic machine behavior) ---
        # Machines randomly stop occasionally (simulates natural production cycles)
        if s.status == MachineStatus.RUNNING and self._tick_count % 300 == 0:
            if random.random() < 0.15:  # 15% chance every 300 ticks = rare stops
                self.stop("CYCLE_COMPLETE")
                # Auto-restart after a brief pause
                self._schedule_restart = True

        # Auto-restart after planned stop
        if hasattr(self, '_schedule_restart') and self._schedule_restart:
            if random.random() < 0.3:  # Random delay before restart
                self.start()
                self._schedule_restart = False

    def get_snapshot(self) -> dict:
        """
        Returns the current machine state as a dictionary.
        This is what the PLC reads on each scan cycle.
        """
        return {
            "machine_id": self.config.machine_id,
            "machine_name": self.config.machine_name,
            "machine_type": self.config.machine_type,
            "plant_id": self.config.plant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": self.state.status.value,
            "current_rpm": round(self.state.current_rpm, 1),
            "target_rpm": round(self.state.target_rpm, 1),
            "temperature": round(self.state.temperature, 2),
            "pressure": round(self.state.pressure, 3),
            "vibration": round(self.state.vibration, 3),
            "power_consumption": round(self.state.power_consumption, 3),
            "production_count": self.state.production_count,
            "error_code": self.state.error_code,
            "fault_active": self.state.fault_active,
            "fault_type": self.state.fault_type,
            # Limits (for reference by PLC and dashboard)
            "temperature_limit": self.config.temperature_limit,
            "vibration_limit": self.config.vibration_limit,
            "pressure_limit": self.config.pressure_limit,
        }


def create_fleet() -> list[MachineSimulator]:
    """
    Creates and starts all machines in the simulated fleet.
    Some machines start running, some start stopped — realistic shift start.
    """
    simulators = []
    for config in MACHINE_FLEET:
        sim = MachineSimulator(config)
        # Start most machines running — simulate mid-shift
        if config.machine_id in ("CNC-001", "CNC-002", "MILL-001"):
            sim.start()
        # CNC-003 starts stopped (simulating a scheduled maintenance window)
        # PRESS-001 starts stopped (awaiting material)
        simulators.append(sim)
    return simulators
