"""
api/v1/digital_twin.py — Digital Twin REST Endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.digital_twin import DigitalTwinResponse
from app.services.digital_twin import digital_twin_service

router = APIRouter(tags=["Digital Twin"])


@router.get(
    "/machines/{machine_id}/digital-twin",
    response_model=DigitalTwinResponse,
    summary="Get Unified Digital Twin Representation",
)
async def get_digital_twin(machine_id: str, db: AsyncSession = Depends(get_async_session)):
    """
    Returns the complete Digital Twin for a given machine:
    - Metadata & design limits
    - Live sensor state
    - Transparent health score calculation breakdown
    - Prototype predictive maintenance risk & recommendation
    - Production and downtime KPIs
    - Active operational alerts
    """
    twin = await digital_twin_service.get_digital_twin(db, machine_id.upper())
    if not twin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id.upper()}' not found",
        )
    return twin
