"""
simulator/main.py — Simulator Entrypoint & Orchestration Loop
==============================================================

This is the main process for the ForgePulse machine simulator.
It orchestrates:
  1. Machine fleet initialization (MachineSimulator instances)
  2. PLC fleet initialization (SoftwarePLC instances)
  3. MQTT publisher connection to broker
  4. Main simulation loop (tick → scan → publish → repeat)
  5. Fault injection control via environment variables or API
  6. Graceful shutdown on SIGTERM/SIGINT (Docker stop)

EXECUTION FLOW (every PUBLISH_INTERVAL_SECONDS):
  For each machine:
    machine_sim.tick(dt)                   # Advance physics state
    plc.scan(machine_sim.get_snapshot())   # PLC reads sensor values
    payload = plc.build_telemetry_payload()# Format MQTT message
    publisher.publish_telemetry(payload)   # Send to MQTT broker
    publisher.publish_status(status)       # Update retained status topic

ENVIRONMENT VARIABLES:
  MQTT_BROKER_HOST       — default: localhost
  MQTT_BROKER_PORT       — default: 1883
  MQTT_CLIENT_ID         — default: forgepulse-simulator
  MQTT_TOPIC_PREFIX      — default: factory
  PUBLISH_INTERVAL_SECONDS — default: 2
"""

import logging
import os
import signal
import sys
import time
import json
import threading
from typing import Optional

# Configure basic logging for the simulator (standalone process, no FastAPI)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("forgepulse.simulator")

# Import simulator modules
from machine_simulator import create_fleet, MachineSimulator, MachineStatus
from plc_simulator import create_plc_fleet, SoftwarePLC
from fault_injection import FaultInjector, FAULT_SCENARIOS
from mqtt_publisher import MQTTPublisher


def get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)


class SimulatorOrchestrator:
    """
    Main simulation orchestrator.
    Manages the fleet, PLCs, publisher, and main loop.
    """

    def __init__(self) -> None:
        # Configuration from environment
        self.broker_host = get_env("MQTT_BROKER_HOST", "localhost")
        self.broker_port = int(get_env("MQTT_BROKER_PORT", "1883"))
        self.client_id = get_env("MQTT_CLIENT_ID", "forgepulse-simulator")
        self.topic_prefix = get_env("MQTT_TOPIC_PREFIX", "factory")
        self.publish_interval = float(get_env("PUBLISH_INTERVAL_SECONDS", "2"))
        self.mqtt_username = get_env("MQTT_USERNAME", "") or None
        self.mqtt_password = get_env("MQTT_PASSWORD", "") or None

        # Fleet state
        self._machine_fleet: list[MachineSimulator] = []
        self._machine_map: dict[str, MachineSimulator] = {}
        self._plc_map: dict[str, SoftwarePLC] = {}
        self._publisher: Optional[MQTTPublisher] = None
        self._fault_injector = FaultInjector()

        # Control
        self._running = False
        self._tick_count = 0

        # Register shutdown handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def initialize(self) -> bool:
        """Initialize fleet, PLCs, and MQTT connection."""
        logger.info("=" * 60)
        logger.info("  FORGEPULSE Machine Simulator Starting")
        logger.info("  NOTE: This is a software simulation.")
        logger.info("  No real industrial hardware is connected.")
        logger.info("=" * 60)

        # Create machine fleet
        self._machine_fleet = create_fleet()
        self._machine_map = {sim.config.machine_id: sim for sim in self._machine_fleet}
        logger.info(f"Machine fleet initialized: {list(self._machine_map.keys())}")

        # Create PLC fleet
        self._plc_map = create_plc_fleet(self._machine_fleet)
        logger.info(f"Software PLC fleet initialized: {list(self._plc_map.keys())}")

        # Connect MQTT publisher
        self._publisher = MQTTPublisher(
            broker_host=self.broker_host,
            broker_port=self.broker_port,
            client_id=self.client_id,
            topic_prefix=self.topic_prefix,
            qos=1,
            username=self.mqtt_username,
            password=self.mqtt_password,
        )

        connected = self._publisher.connect(max_retries=20, retry_delay=3.0)
        if not connected:
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return False

        logger.info(
            f"MQTT publisher connected to {self.broker_host}:{self.broker_port}"
        )
        logger.info(
            f"Simulation interval: {self.publish_interval}s "
            f"({5 / self.publish_interval:.1f} Hz per machine × 5 machines)"
        )
        return True

    def run(self) -> None:
        """Main simulation loop."""
        self._running = True
        last_tick_time = time.time()

        logger.info("Simulation loop started. Publishing telemetry...")

        while self._running:
            loop_start = time.time()

            # Calculate actual dt (time since last tick)
            dt = loop_start - last_tick_time
            last_tick_time = loop_start
            self._tick_count += 1

            # Check for expired fault injections
            cleared = self._fault_injector.check_expirations(self._machine_map)
            for machine_id in cleared:
                logger.info(f"Fault auto-cleared on {machine_id} (duration expired)")

            # Process each machine in the fleet
            for machine_sim in self._machine_fleet:
                machine_id = machine_sim.config.machine_id
                plant_id = machine_sim.config.plant_id
                plc = self._plc_map[machine_id]

                try:
                    # Step 1: Advance machine physics
                    machine_sim.tick(dt=self.publish_interval)

                    # Step 2: PLC scan — reads machine state, applies scaling
                    snapshot = machine_sim.get_snapshot()
                    scan_result = plc.scan(snapshot)

                    # Step 3: Build MQTT payload
                    payload = plc.build_telemetry_payload(
                        scan_result,
                        production_count=machine_sim.state.production_count
                    )

                    # Step 4: Publish telemetry
                    self._publisher.publish_telemetry(plant_id, machine_id, payload)

                    # Step 5: Publish retained status (so new subscribers see current state)
                    self._publisher.publish_status(
                        plant_id, machine_id, scan_result.machine_status
                    )

                    # Log a summary line at info level (not every message to avoid noise)
                    if self._tick_count % 10 == 0:
                        logger.info(
                            f"{machine_id} | {scan_result.machine_status:11s} | "
                            f"T={scan_result.tags['temperature'].value:5.1f}°C | "
                            f"V={scan_result.tags['vibration'].value:5.3f}mm/s | "
                            f"P={scan_result.tags['power'].value:5.2f}kW | "
                            f"Prod={machine_sim.state.production_count}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing machine {machine_id}: {e}",
                        exc_info=True,
                    )
                    # Continue with next machine — don't let one failure kill the loop

            # Print overall stats every 60 ticks
            if self._tick_count % 60 == 0 and self._publisher:
                stats = self._publisher.stats
                logger.info(
                    f"Publisher stats: published={stats['published']}, "
                    f"failed={stats['failed']}, reconnects={stats['reconnects']}"
                )

            # Sleep to maintain the desired publish interval
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.publish_interval - elapsed)
            if sleep_time < 0.1 and elapsed > self.publish_interval * 1.5:
                logger.warning(
                    f"Simulation loop is slow: {elapsed:.2f}s (target: {self.publish_interval}s)"
                )
            time.sleep(sleep_time)

    def inject_fault(self, machine_id: str, fault_name: str) -> dict:
        """
        External fault injection interface.
        Called by the FastAPI backend via POST /simulate-failure.
        Thread-safe — the main loop checks fault state on each tick.
        """
        if machine_id not in self._machine_map:
            raise ValueError(f"Unknown machine: {machine_id}")

        simulator = self._machine_map[machine_id]
        result = self._fault_injector.inject(machine_id, fault_name, simulator)

        # Publish an event message to the events topic
        if self._publisher:
            event = {
                "event_type": "FAULT_INJECTED",
                "machine_id": machine_id,
                "fault_name": fault_name,
                "fault_type": result["fault_type"],
                "intensity": result["intensity"],
                "source": "forgepulse-fault-injector",
            }
            self._publisher.publish_event(
                self._machine_map[machine_id].config.plant_id,
                machine_id,
                event,
            )

        logger.warning(
            f"FAULT INJECTED: {fault_name} on {machine_id} "
            f"(intensity={result['intensity']})"
        )
        return result

    def clear_fault(self, machine_id: str) -> dict:
        """Clear any active fault on a machine."""
        if machine_id not in self._machine_map:
            raise ValueError(f"Unknown machine: {machine_id}")
        result = self._fault_injector.clear(machine_id, self._machine_map[machine_id])
        logger.info(f"Fault cleared on {machine_id}")
        return result

    def start_machine(self, machine_id: str) -> dict:
        """Start a stopped machine."""
        if machine_id not in self._machine_map:
            raise ValueError(f"Unknown machine: {machine_id}")
        self._machine_map[machine_id].start()
        return {"machine_id": machine_id, "action": "STARTED"}

    def stop_machine(self, machine_id: str) -> dict:
        """Stop a running machine."""
        if machine_id not in self._machine_map:
            raise ValueError(f"Unknown machine: {machine_id}")
        self._machine_map[machine_id].stop("OPERATOR_COMMAND")
        return {"machine_id": machine_id, "action": "STOPPED"}

    def get_status(self) -> dict:
        """Returns current status of all machines (for diagnostics)."""
        return {
            "tick_count": self._tick_count,
            "publish_interval": self.publish_interval,
            "mqtt_stats": self._publisher.stats if self._publisher else {},
            "active_faults": self._fault_injector.get_active_faults(),
            "machines": {
                mid: {
                    "status": sim.state.status.value,
                    "temperature": round(sim.state.temperature, 2),
                    "vibration": round(sim.state.vibration, 3),
                    "rpm": round(sim.state.current_rpm, 1),
                    "production_count": sim.state.production_count,
                    "fault_active": sim.state.fault_active,
                }
                for mid, sim in self._machine_map.items()
            },
        }

    def _handle_shutdown(self, signum, frame) -> None:
        """Graceful shutdown handler for SIGTERM/SIGINT (Docker stop)."""
        logger.info(f"Shutdown signal {signum} received. Stopping simulation...")
        self._running = False
        if self._publisher:
            # Publish STOPPED status for all machines before disconnecting
            for machine_sim in self._machine_fleet:
                try:
                    self._publisher.publish_status(
                        machine_sim.config.plant_id,
                        machine_sim.config.machine_id,
                        "STOPPED",
                    )
                except Exception:
                    pass
            self._publisher.disconnect()
        logger.info("Simulator shutdown complete.")
        sys.exit(0)


# Module-level singleton — accessible from API control endpoints
_orchestrator: Optional[SimulatorOrchestrator] = None


def get_orchestrator() -> SimulatorOrchestrator:
    """Returns the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SimulatorOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    orchestrator = get_orchestrator()

    if orchestrator.initialize():
        try:
            orchestrator.run()
        except Exception as e:
            logger.critical(f"Simulator crashed: {e}", exc_info=True)
            sys.exit(1)
    else:
        sys.exit(1)
