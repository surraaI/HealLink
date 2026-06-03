from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_provider, get_db
from app.models.provider import Provider
from app.schemas.schedule import (
    GenerateSlotsRequest,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    SlotGenerationResponse,
)
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])
schedule_service = ScheduleService()


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    payload: ScheduleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> ScheduleResponse:
    """Create a new schedule for the provider."""
    schedule = await schedule_service.create_schedule(
        db,
        provider_id=current_provider.id,
        service_id=payload.service_id,
        schedule_type=payload.schedule_type,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    return ScheduleResponse.model_validate(schedule)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: Annotated[int, Query()],
    service_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> list[ScheduleResponse]:
    """List all schedules for a provider (public endpoint)."""
    schedules = await schedule_service.list_provider_schedules(
        db,
        provider_id=provider_id,
        service_id=service_id,
        is_active=is_active,
    )
    return [ScheduleResponse.model_validate(schedule) for schedule in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: Annotated[int, Query()],
) -> ScheduleResponse:
    """Get a specific schedule by ID (public endpoint)."""
    schedule = await schedule_service.get_schedule(db, schedule_id, provider_id)
    return ScheduleResponse.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> ScheduleResponse:
    """Update an existing schedule."""
    schedule = await schedule_service.update_schedule(
        db,
        schedule_id=schedule_id,
        provider_id=current_provider.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        is_active=payload.is_active,
    )
    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> dict:
    """Delete a schedule."""
    await schedule_service.delete_schedule(db, schedule_id, current_provider.id)
    return {"message": "Schedule deleted successfully"}


@router.post("/{schedule_id}/generate-slots", response_model=SlotGenerationResponse)
async def generate_slots(
    schedule_id: int,
    payload: GenerateSlotsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> SlotGenerationResponse:
    """Generate service slots for a specific date based on a schedule."""
    schedule = await schedule_service.get_schedule(db, schedule_id, current_provider.id)
    slots = await schedule_service.generate_slots_from_schedule(db, schedule, payload.date)
    return SlotGenerationResponse(
        message=f"Generated {len(slots)} slots for {payload.date.date()}",
        slots_created=len(slots),
    )
