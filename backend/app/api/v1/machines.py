"""
api/v1/machines.py — Machine Fleet Endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.machine import MachineDetailResponse, MachineResponse
from app.services.machine_service import machine_service

router = APIRouter(prefix="/machines", tags=["Machines"])


@router.get("", response_model=List[MachineResponse], summary="List All Machines")
async def list_machines(db: AsyncSession = Depends(get_async_session)):
    """Returns all active machines on the simulated shop floor."""
    return await machine_service.get_all_machines(db)


@router.get("/{machine_id}", response_model=MachineDetailResponse, summary="Get Machine Details")
async def get_machine(machine_id: str, db: AsyncSession = Depends(get_async_session)):
    """Returns full metadata and configured sensors for a specific machine."""
    machine = await machine_service.get_machine_by_id(db, machine_id.upper())
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id.upper()}' not found",
        )
    return machine
