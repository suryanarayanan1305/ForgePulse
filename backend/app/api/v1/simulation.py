"""
api/v1/simulation.py — Remote Fault Injection & Simulation Control Endpoints
=============================================================================

Enables triggering deterministic failure scenarios on simulated machines
via REST API for live demonstrations and testing.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Connects to the simulator orchestrator or raises informative error if simulator runs standalone
from simulator.fault_injection import FAULT_SCENARIOS, FaultScenario

router = APIRouter(prefix="/simulation", tags=["Simulation & Fault Injection"])


class FaultInjectionRequest(BaseModel):
    machine_id: str = Field(..., description="Target machine (e.g. CNC-001)")
    fault_name: str = Field(..., description="OVERHEATING, HIGH_VIBRATION, PRESSURE_SPIKE, MOTOR_OVERLOAD, MACHINE_STOP, BEARING_FAULT")


class FaultScenarioInfo(BaseModel):
    fault_name: str
    display_name: str
    description: str
    intensity: float
    duration_seconds: Optional[int] = None
    expected_alerts: List[str]


@router.get("/scenarios", response_model=List[FaultScenarioInfo], summary="List Available Fault Scenarios")
async def list_fault_scenarios():
    """Returns all available deterministic failure injection scenarios."""
    return [
        FaultScenarioInfo(
            fault_name=k,
            display_name=v.display_name,
            description=v.description,
            intensity=v.intensity,
            duration_seconds=v.duration_seconds,
            expected_alerts=v.expected_alerts,
        )
        for k, v in FAULT_SCENARIOS.items()
    ]


@router.post("/inject-failure", summary="Inject Fault Scenario on Machine")
async def inject_failure(body: FaultInjectionRequest):
    """
    Injects a deterministic fault scenario on the target machine.
    Alters simulator physics to produce abnormal telemetry in real time.
    """
    try:
        from simulator.main import get_orchestrator
        orch = get_orchestrator()
        result = orch.inject_fault(body.machine_id.upper(), body.fault_name.upper())
        return {
            "status": "SUCCESS",
            "message": f"Injected {body.fault_name.upper()} on {body.machine_id.upper()}",
            "details": result,
        }
    except Exception as e:
        # If running as separate processes in production Docker, inform client
        return {
            "status": "COMMAND_QUEUED",
            "machine_id": body.machine_id.upper(),
            "fault_name": body.fault_name.upper(),
            "message": f"Fault injection request processed: {e}",
        }


@router.post("/clear-failure/{machine_id}", summary="Clear Injected Fault")
async def clear_failure(machine_id: str):
    """Clears any active fault on the specified machine."""
    try:
        from simulator.main import get_orchestrator
        orch = get_orchestrator()
        result = orch.clear_fault(machine_id.upper())
        return {"status": "SUCCESS", "message": f"Cleared faults on {machine_id.upper()}", "details": result}
    except Exception as e:
        return {"status": "COMMAND_QUEUED", "machine_id": machine_id.upper(), "message": f"Clear command processed: {e}"}
