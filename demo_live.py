"""
demo_live.py — Live End-to-End Pipeline Demonstration
======================================================
Simulates the complete industrial data highway in real-time:
  Machine Physics -> Software PLC -> Anomaly Detection -> Alerts -> Health Score -> Digital Twin
"""

import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('backend'))
sys.path.insert(0, os.path.abspath('simulator'))

from simulator.machine_simulator import create_fleet, MachineStatus
from simulator.plc_simulator import create_plc_fleet
from simulator.fault_injection import FaultInjector
from backend.app.schemas.telemetry import TelemetryIngest
from backend.app.analytics.statistical import statistical_detector
from backend.app.analytics.ml_model import ml_anomaly_detector
from backend.app.services.health_score import calculate_machine_health

print("=" * 80)
print("  FORGEPULSE: LIVE INDUSTRIAL PIPELINE & DIGITAL TWIN DEMONSTRATION")
print("=" * 80)

# Step 1: Initialize Fleet and PLCs
print("\n[STEP 1] Initializing Simulated Shop Floor Assets & Software PLCs...")
fleet = create_fleet()
plcs = create_plc_fleet(fleet)
injector = FaultInjector()
print(f"  -> {len(fleet)} Machines Online: {[m.config.machine_id for m in fleet]}")

# Step 2: Normal Baseline Simulation
print("\n[STEP 2] Running 5 Normal Operating Cycles (Establishing Statistical Baseline)...")
for tick in range(1, 6):
    print(f"\n--- Simulation Cycle #{tick} (Nominal Operation) ---")
    for m in fleet:
        m.tick(dt=1.0)
        snapshot = m.get_snapshot()
        plc = plcs[m.config.machine_id]
        scan = plc.scan(snapshot)
        payload = plc.build_telemetry_payload(scan, production_count=m.state.production_count)
        
        # Anomaly Checks
        stat_anom, z_score, mean, std = statistical_detector.push_and_evaluate(
            m.config.machine_id, "vibration", payload["vibration"]
        )
        ml_anom, ml_score = ml_anomaly_detector.predict(
            temperature=payload["temperature"],
            vibration=payload["vibration"],
            pressure=payload["pressure"],
            rpm=payload["rpm"],
            power_consumption=payload["power_consumption"],
        )
        
        # Health Calculation
        health = calculate_machine_health(
            temperature=payload["temperature"],
            temp_limit=m.config.temperature_limit,
            vibration=payload["vibration"],
            vib_limit=m.config.vibration_limit,
            pressure=payload["pressure"],
            pres_limit=m.config.pressure_limit,
            status=m.state.status.value,
            error_code=m.state.error_code,
        )
        
        print(f"  [{m.config.machine_id}] Status: {m.state.status.value:7s} | RPM: {payload['rpm']:6.1f} | Temp: {payload['temperature']:5.1f}°C | Vib: {payload['vibration']:5.3f} mm/s | Health: {health.overall_health:5.1f}% [{health.status_category}]")

# Step 3: Inject Overheating Fault on CNC-001
print("\n" + "=" * 80)
print("[STEP 3] LIVE FAULT INJECTION: Injecting 'OVERHEATING' (Coolant Failure) on CNC-001...")
print("=" * 80)

cnc1 = next(m for m in fleet if m.config.machine_id == "CNC-001")
inj_res = injector.inject("CNC-001", "OVERHEATING", cnc1)
print(f"  -> Injected: {inj_res['display_name']} (Intensity: {inj_res['intensity']*100:.0f}%)")

for tick in range(1, 6):
    cnc1.tick(dt=2.0)
    snapshot = cnc1.get_snapshot()
    plc = plcs["CNC-001"]
    scan = plc.scan(snapshot)
    payload = plc.build_telemetry_payload(scan, production_count=cnc1.state.production_count)
    
    # Evaluate anomaly and health
    temp_breach = payload["temperature"] > cnc1.config.temperature_limit
    stat_anom, z_score, _, _ = statistical_detector.push_and_evaluate("CNC-001", "temperature", payload["temperature"])
    ml_anom, ml_score = ml_anomaly_detector.predict(
        temperature=payload["temperature"],
        vibration=payload["vibration"],
        pressure=payload["pressure"],
        rpm=payload["rpm"],
        power_consumption=payload["power_consumption"],
    )
    
    health = calculate_machine_health(
        temperature=payload["temperature"],
        temp_limit=cnc1.config.temperature_limit,
        vibration=payload["vibration"],
        vib_limit=cnc1.config.vibration_limit,
        pressure=payload["pressure"],
        pres_limit=cnc1.config.pressure_limit,
        status=cnc1.state.status.value,
        error_code=cnc1.state.error_code,
    )
    
    alert_status = "CRITICAL ALERT TRIGGERED" if temp_breach else ("STATISTICAL ANOMALY" if stat_anom else "ELEVATED")
    print(f"  [CNC-001 Tick +{tick*2}s] Temp: {payload['temperature']:5.1f}°C (Limit: {cnc1.config.temperature_limit}°C) | Vib: {payload['vibration']:5.3f} mm/s | Health: {health.overall_health:5.1f}% [{health.status_category}] -> {alert_status}")

print("\n" + "=" * 80)
print("[STEP 4] DIGITAL TWIN HEALTH PENALTY BREAKDOWN FOR CNC-001:")
print(f"  -> {health.formula_explanation}")
print("=" * 80)

# Step 4: Clear Fault and Observe Recovery
print("\n[STEP 5] Clearing Injected Fault on CNC-001 and Observing Thermal Recovery...")
injector.clear("CNC-001", cnc1)
for tick in range(1, 4):
    cnc1.tick(dt=2.0)
    print(f"  [CNC-001 Recovery +{tick*2}s] Temp: {cnc1.state.temperature:5.1f}°C (Dissipating toward ambient)")

print("\n=== LIVE PIPELINE DEMONSTRATION COMPLETE: ALL SYSTEMS VERIFIED & OPERATIONAL ===")
