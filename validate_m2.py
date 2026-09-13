"""
Validation script for Milestone 2:
Tests Machine Simulator physics, PLC tag scaling, fault injection, and payload formatting.
"""
import sys
import os

sys.path.insert(0, os.path.abspath('simulator'))

from machine_simulator import create_fleet, MachineStatus
from plc_simulator import create_plc_fleet, scale_4_20ma, engineering_to_4_20ma
from fault_injection import FaultInjector, FAULT_SCENARIOS

print("=== STARTING MILESTONE 2 VALIDATION ===")

# 1. Verify 4-20mA scaling math
scaled = scale_4_20ma(12.0, 0.0, 100.0)
assert scaled == 50.0, f"Expected 50.0, got {scaled}"
raw_ma = engineering_to_4_20ma(50.0, 0.0, 100.0)
assert raw_ma == 12.0, f"Expected 12.0, got {raw_ma}"
print("[PASS] 4-20mA scaling and inverse conversion verified")

# 2. Verify Fleet and PLC initialization
machines = create_fleet()
assert len(machines) == 5, f"Expected 5 machines, got {len(machines)}"
plcs = create_plc_fleet(machines)
assert len(plcs) == 5, f"Expected 5 PLCs, got {len(plcs)}"
print(f"[PASS] Fleet and PLCs created for {[m.config.machine_id for m in machines]}")

# 3. Simulate 10 ticks and verify physics response
cnc1 = next(m for m in machines if m.config.machine_id == "CNC-001")
cnc1.start(target_rpm=6000.0)
initial_temp = cnc1.state.temperature

for _ in range(15):
    cnc1.tick(dt=1.0)

plc = plcs["CNC-001"]
snapshot = cnc1.get_snapshot()
scan_result = plc.scan(snapshot)
payload = plc.build_telemetry_payload(scan_result, production_count=cnc1.state.production_count)

assert cnc1.state.current_rpm > 0, "RPM should have ramped up"
assert payload["temperature"] > 0, "Temperature should be positive"
assert "temperature" in scan_result.tags, "PLC tag table missing temperature"
assert payload["_plc_meta"]["scan_count"] > 0, "PLC scan count should increment"
print(f"[PASS] Running CNC-001: RPM={cnc1.state.current_rpm:.1f}, Temp={payload['temperature']}°C, Vib={payload['vibration']}mm/s")

# 4. Test Fault Injection
injector = FaultInjector()
result = injector.inject("CNC-001", "OVERHEATING", cnc1)
assert cnc1.state.fault_active is True
assert result["status"] == "INJECTED"

# Advance physics with fault active
for _ in range(10):
    cnc1.tick(dt=1.0)

fault_temp = cnc1.state.temperature
assert fault_temp > initial_temp, f"Temperature should climb during overheating fault (was {initial_temp}, now {fault_temp})"
print(f"[PASS] Overheating fault verified: Temperature increased to {fault_temp:.2f}°C")

# Test fault clearing
clear_res = injector.clear("CNC-001", cnc1)
assert cnc1.state.fault_active is False
print("[PASS] Fault clear verified")

print("\n=== ALL MILESTONE 2 VALIDATION TESTS PASSED SUCCESSFULLY ===")
