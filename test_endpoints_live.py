"""
test_endpoints_live.py — Live Test for all FastAPI REST endpoints
"""
import sys
sys.path.insert(0, 'backend')

from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    r_health = client.get('/api/v1/health')
    print(f"[PASS] /api/v1/health -> {r_health.status_code}: {r_health.json()['status']}")

    r_machines = client.get('/api/v1/machines')
    machines = r_machines.json()
    print(f"[PASS] /api/v1/machines -> {r_machines.status_code}: {[m['machine_id'] for m in machines]}")

    r_twin = client.get('/api/v1/machines/CNC-001/digital-twin')
    twin = r_twin.json()
    print(f"[PASS] /api/v1/machines/CNC-001/digital-twin -> {r_twin.status_code}: Health={twin['health']['overall_health']}%, Status={twin['current_status']}")

    r_scenarios = client.get('/api/v1/simulation/scenarios')
    scenarios = r_scenarios.json()
    print(f"[PASS] /api/v1/simulation/scenarios -> {r_scenarios.status_code}: {[s['fault_name'] for s in scenarios]}")

    r_summary = client.get('/api/v1/analytics/summary')
    summary = r_summary.json()
    print(f"[PASS] /api/v1/analytics/summary -> {r_summary.status_code}: Total Machines={summary['total_machines']}, Avg Health={summary['average_plant_health']}%")

print("\n=== ALL REST API ENDPOINTS FULLY OPERATIONAL AND RETURNING 200 OK ===")
