"""
simulator/plc_simulator.py — Software PLC Abstraction
=======================================================

DISCLAIMER:
  This is a SOFTWARE ABSTRACTION of a PLC, created because this project
  does not have access to physical industrial PLC hardware (Siemens S7,
  Allen-Bradley ControlLogix, etc.).

  A real PLC would:
    1. Read 4-20mA analog signals from field sensors
    2. Scale them to engineering units (0mA=min, 20mA=max → 4-20mA formula)
    3. Execute ladder logic or function block diagrams on each scan cycle
    4. Maintain a "tag table" — a real-time database of current process values
    5. Communicate via OPC-UA, Modbus TCP, or PROFINET to SCADA/MES

  This software PLC:
    1. Reads from the MachineSimulator physics state (instead of hardware I/O)
    2. Applies engineering unit scaling and range clamping
    3. Evaluates machine status logic
    4. Maintains a tag table in memory
    5. Hands off formatted data to the IoT Gateway (MQTT publisher)

WHY HAVE A SEPARATE PLC LAYER?
  In a real IIoT architecture, the PLC and the IoT gateway are separate systems.
  The PLC maintains operational state at millisecond scan rates (real-time control).
  The IoT gateway reads PLC tags at a slower rate (1-5 seconds) and forwards them.
  Keeping these layers separate in our simulation reflects the real architecture —
  important for the Forward Deployed Engineer interview.

PLC TAG TABLE:
  A dictionary mapping tag names to current values, updated every scan cycle.
  This is the "single source of truth" that the IoT gateway reads from.

4-20mA SCALING:
  The formula: engineering_value = min_val + (raw_mA - 4) / 16 * (max_val - min_val)
  Example: temperature sensor reads 12mA → 20°C + (12-4)/16 * (85-20) = 52.5°C
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PLCTag:
    """
    Represents a single PLC tag (a named, typed process variable).

    In a real Siemens S7 PLC, this maps to a DB (Data Block) address.
    In Allen-Bradley, this is a tag in the controller's tag database.
    """
    name: str           # Tag name: e.g., "CNC001_SPINDLE_TEMP"
    value: float        # Current engineering unit value
    unit: str           # Engineering unit: "°C", "mm/s", "bar", "RPM", "kW"
    raw_signal: float   # Simulated 4-20mA raw value (for realism)
    quality: str        # "GOOD", "BAD", "UNCERTAIN" — OPC-UA concept
    timestamp: str      # When this tag was last updated


@dataclass
class PLCScanResult:
    """
    The output of one PLC scan cycle — the formatted data packet
    that the IoT gateway will read and forward as an MQTT message.
    """
    machine_id: str
    plant_id: str
    scan_timestamp: str
    tags: dict[str, PLCTag]

    # Derived machine-level values
    machine_status: str
    error_code: Optional[str]
    is_healthy: bool


def scale_4_20ma(raw_ma: float, min_val: float, max_val: float) -> float:
    """
    Scales a simulated 4-20mA signal to engineering units.

    INTERVIEW CONTEXT:
      "4-20mA is the most common industrial sensor signal standard.
       4mA = minimum range (not 0mA, to detect broken wire: 0mA = fault).
       20mA = maximum range.
       Formula: EU = min + (mA - 4) / 16 * (max - min)"

    Args:
        raw_ma: Simulated raw milliamp signal (4.0 to 20.0)
        min_val: Engineering unit at 4mA
        max_val: Engineering unit at 20mA

    Returns:
        Scaled engineering unit value
    """
    # Clamp to valid 4-20mA range
    raw_ma = max(4.0, min(20.0, raw_ma))
    return min_val + (raw_ma - 4.0) / 16.0 * (max_val - min_val)


def engineering_to_4_20ma(eu_value: float, min_val: float, max_val: float) -> float:
    """
    Converts an engineering unit value back to a 4-20mA representation.
    Used to simulate the analog signal from the physics engine.
    """
    if max_val == min_val:
        return 4.0
    ratio = max(0.0, min(1.0, (eu_value - min_val) / (max_val - min_val)))
    return 4.0 + ratio * 16.0


class SoftwarePLC:
    """
    Software PLC for a single machine.

    Scan Cycle:
      The PLC executes its program on every scan_cycle_ms interval.
      We call scan() from the main simulation loop.

    Tag Table:
      After each scan, the tag_table dict holds the latest values of all
      process variables for this machine.
    """

    # Scan cycle = 1000ms (1 Hz) — realistic for IoT monitoring
    # Real PLCs scan at 10-100ms for control; we use 1s because we're monitoring
    SCAN_CYCLE_MS = 1000

    def __init__(self, machine_id: str, machine_type: str, config: dict) -> None:
        """
        Args:
            machine_id: Machine identifier (e.g., "CNC-001")
            machine_type: "CNC", "PRESS", "MILL"
            config: MachineConfig attributes as dict (limits, rated values)
        """
        self.machine_id = machine_id
        self.machine_type = machine_type
        self.config = config
        self.tag_table: dict[str, PLCTag] = {}
        self.scan_count = 0
        self.last_scan_time: Optional[str] = None

    def scan(self, machine_snapshot: dict) -> PLCScanResult:
        """
        Execute one PLC scan cycle.

        Reads the machine physics snapshot (simulated sensor readings),
        applies 4-20mA scaling and engineering unit processing,
        evaluates machine status logic,
        and updates the tag table.

        Args:
            machine_snapshot: Output of MachineSimulator.get_snapshot()

        Returns:
            PLCScanResult with all tags and derived status
        """
        self.scan_count += 1
        now = datetime.now(timezone.utc).isoformat()
        self.last_scan_time = now

        cfg = self.config
        s = machine_snapshot

        # --- TEMPERATURE TAG ---
        # Simulate 4-20mA from temperature sensor
        # 4mA = 0°C, 20mA = 120°C (typical thermocouple transmitter range)
        temp_ma = engineering_to_4_20ma(s["temperature"], 0.0, 120.0)
        temp_scaled = scale_4_20ma(temp_ma, 0.0, 120.0)

        temp_tag = PLCTag(
            name=f"{self.machine_id}_TEMPERATURE",
            value=round(temp_scaled, 2),
            unit="°C",
            raw_signal=round(temp_ma, 3),
            quality=self._get_signal_quality(temp_ma, 4.0, 20.0),
            timestamp=now,
        )

        # --- VIBRATION TAG ---
        # 4mA = 0 mm/s, 20mA = 20 mm/s
        vib_ma = engineering_to_4_20ma(s["vibration"], 0.0, 20.0)
        vib_scaled = scale_4_20ma(vib_ma, 0.0, 20.0)

        vib_tag = PLCTag(
            name=f"{self.machine_id}_VIBRATION",
            value=round(vib_scaled, 3),
            unit="mm/s",
            raw_signal=round(vib_ma, 3),
            quality=self._get_signal_quality(vib_ma, 4.0, 20.0),
            timestamp=now,
        )

        # --- PRESSURE TAG ---
        # Range depends on machine type
        if self.machine_type == "PRESS":
            p_min, p_max = 0.0, 300.0   # bar (hydraulic)
        else:
            p_min, p_max = 0.0, 15.0    # bar (coolant)

        pres_ma = engineering_to_4_20ma(s["pressure"], p_min, p_max)
        pres_scaled = scale_4_20ma(pres_ma, p_min, p_max)

        pres_tag = PLCTag(
            name=f"{self.machine_id}_PRESSURE",
            value=round(pres_scaled, 3),
            unit="bar",
            raw_signal=round(pres_ma, 3),
            quality=self._get_signal_quality(pres_ma, 4.0, 20.0),
            timestamp=now,
        )

        # --- RPM TAG ---
        # 4mA = 0 RPM, 20mA = rated_rpm * 1.2 (headroom)
        rpm_max = cfg.get("rated_rpm", 6000) * 1.2
        rpm_ma = engineering_to_4_20ma(s["current_rpm"], 0.0, rpm_max)
        rpm_scaled = scale_4_20ma(rpm_ma, 0.0, rpm_max)

        rpm_tag = PLCTag(
            name=f"{self.machine_id}_RPM",
            value=round(rpm_scaled, 1),
            unit="RPM",
            raw_signal=round(rpm_ma, 3),
            quality=self._get_signal_quality(rpm_ma, 4.0, 20.0),
            timestamp=now,
        )

        # --- POWER TAG ---
        # 4mA = 0 kW, 20mA = power_limit * 1.1
        pwr_max = cfg.get("power_limit", 30.0) * 1.1
        pwr_ma = engineering_to_4_20ma(s["power_consumption"], 0.0, pwr_max)
        pwr_scaled = scale_4_20ma(pwr_ma, 0.0, pwr_max)

        pwr_tag = PLCTag(
            name=f"{self.machine_id}_POWER",
            value=round(pwr_scaled, 3),
            unit="kW",
            raw_signal=round(pwr_ma, 3),
            quality=self._get_signal_quality(pwr_ma, 4.0, 20.0),
            timestamp=now,
        )

        # --- STATUS WORD (Discrete I/O) ---
        # In a real PLC, machine status comes from digital I/O:
        # DI 0.0 = Running bit, DI 0.1 = Fault bit, DI 0.2 = E-stop bit
        machine_status = s["status"]

        # Evaluate fault condition logic (simplified ladder logic equivalent)
        is_temp_fault = temp_scaled > cfg.get("temperature_limit", 85.0)
        is_vib_fault = vib_scaled > cfg.get("vibration_limit", 7.5)
        is_pres_fault = pres_scaled > cfg.get("pressure_limit", 250.0)
        is_healthy = not (is_temp_fault or is_vib_fault or is_pres_fault)

        # --- Update Tag Table ---
        self.tag_table = {
            "temperature": temp_tag,
            "vibration": vib_tag,
            "pressure": pres_tag,
            "rpm": rpm_tag,
            "power": pwr_tag,
        }

        result = PLCScanResult(
            machine_id=self.machine_id,
            plant_id=s.get("plant_id", "PLANT-A"),
            scan_timestamp=now,
            tags=self.tag_table,
            machine_status=machine_status,
            error_code=s.get("error_code"),
            is_healthy=is_healthy,
        )

        return result

    def build_telemetry_payload(self, scan_result: PLCScanResult, production_count: int) -> dict:
        """
        Converts a PLC scan result into the MQTT telemetry payload format.

        This is the "IoT Gateway" step — packaging PLC tag values into
        a JSON payload that the MQTT broker will distribute.

        The payload format is designed so the backend can deserialize it
        with Pydantic validation without any additional processing.

        Returns:
            dict — JSON-serializable telemetry payload
        """
        tags = scan_result.tags

        return {
            "machine_id": scan_result.machine_id,
            "plant_id": scan_result.plant_id,
            "timestamp": scan_result.scan_timestamp,
            "temperature": tags["temperature"].value,
            "pressure": tags["pressure"].value,
            "vibration": tags["vibration"].value,
            "rpm": tags["rpm"].value,
            "power_consumption": tags["power"].value,
            "production_count": production_count,
            "machine_status": scan_result.machine_status,
            "error_code": scan_result.error_code,
            # Include signal quality for diagnostics (raw_signal shows 4-20mA value)
            "_plc_meta": {
                "scan_count": self.scan_count,
                "signals": {
                    tag_name: {
                        "raw_ma": tag.raw_signal,
                        "quality": tag.quality,
                    }
                    for tag_name, tag in tags.items()
                },
            },
        }

    @staticmethod
    def _get_signal_quality(raw_ma: float, min_ma: float, max_ma: float) -> str:
        """
        Determines signal quality based on raw mA signal range.

        INTERVIEW CONTEXT:
          In industrial systems, signal quality is an OPC-UA concept.
          A reading of 0-3mA typically means a broken wire (FAULT condition).
          A reading within the normal 4-20mA range is "GOOD".
          Values at the very edge of range (e.g., exactly 20mA) may indicate saturation.

        Returns: "GOOD", "BAD", or "UNCERTAIN"
        """
        if raw_ma < 3.5:
            return "BAD"         # Broken wire or sensor failure
        if raw_ma > 20.5:
            return "BAD"         # Sensor saturation / over-range
        if raw_ma < 4.0 or raw_ma > 20.0:
            return "UNCERTAIN"   # Borderline — possible calibration drift
        return "GOOD"


def create_plc_fleet(machine_fleet) -> dict[str, SoftwarePLC]:
    """
    Creates a SoftwarePLC instance for each machine in the fleet.

    Returns:
        dict mapping machine_id → SoftwarePLC
    """
    plcs = {}
    for machine in machine_fleet:
        cfg = {
            "rated_rpm": machine.config.rated_rpm,
            "temperature_limit": machine.config.temperature_limit,
            "vibration_limit": machine.config.vibration_limit,
            "pressure_limit": machine.config.pressure_limit,
            "power_limit": machine.config.power_limit,
        }
        plcs[machine.config.machine_id] = SoftwarePLC(
            machine_id=machine.config.machine_id,
            machine_type=machine.config.machine_type,
            config=cfg,
        )
    return plcs
