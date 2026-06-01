from datetime import datetime, time, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import ServiceCatalog
from app.models.provider import Provider, ServiceSlot
from app.models.provider_schedule import ProviderSchedule, ScheduleType


class ScheduleService:
    async def create_schedule(
        self,
        db: AsyncSession,
        provider_id: int,
        service_id: Optional[int],
        schedule_type: ScheduleType,
        day_of_week: Optional[int],
        start_time: time,
        end_time: time,
        slot_duration_minutes: int,
        valid_from: datetime,
        valid_until: Optional[datetime],
    ) -> ProviderSchedule:
        """Create a new provider schedule with conflict prevention."""
        
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time",
            )
        
        # Validate slot duration
        if slot_duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot duration must be positive",
            )
        
        # Validate day_of_week for weekly schedules
        if schedule_type == ScheduleType.WEEKLY and day_of_week is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="day_of_week is required for weekly schedules",
            )
        
        # Validate day_of_week range
        if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="day_of_week must be between 0 (Monday) and 6 (Sunday)",
            )
        
        # Check for overlapping schedules
        await self._check_schedule_conflict(
            db, provider_id, service_id, day_of_week, start_time, end_time
        )
        
        # Create schedule
        schedule = ProviderSchedule(
            provider_id=provider_id,
            service_id=service_id,
            schedule_type=schedule_type,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule
    
    async def list_provider_schedules(
        self,
        db: AsyncSession,
        provider_id: int,
        service_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> list[ProviderSchedule]:
        """List all schedules for a provider."""
        statement = select(ProviderSchedule).where(ProviderSchedule.provider_id == provider_id)
        
        if service_id is not None:
            statement = statement.where(ProviderSchedule.service_id == service_id)
        if is_active is not None:
            statement = statement.where(ProviderSchedule.is_active == is_active)
        
        statement = statement.order_by(ProviderSchedule.day_of_week, ProviderSchedule.start_time)
        result = await db.scalars(statement)
        return list(result.all())
    
    async def get_schedule(self, db: AsyncSession, schedule_id: int, provider_id: int) -> ProviderSchedule:
        """Get a specific schedule by ID."""
        schedule = await db.scalar(
            select(ProviderSchedule).where(
                and_(
                    ProviderSchedule.id == schedule_id,
                    ProviderSchedule.provider_id == provider_id,
                )
            )
        )
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found",
            )
        return schedule
    
    async def update_schedule(
        self,
        db: AsyncSession,
        schedule_id: int,
        provider_id: int,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        slot_duration_minutes: Optional[int] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        is_active: Optional[bool] = None,
    ) -> ProviderSchedule:
        """Update an existing schedule."""
        schedule = await self.get_schedule(db, schedule_id, provider_id)
        
        # Check for conflicts if time is being updated
        if start_time or end_time:
            new_start = start_time if start_time is not None else schedule.start_time
            new_end = end_time if end_time is not None else schedule.end_time
            
            if new_start >= new_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start time must be before end time",
                )
            
            await self._check_schedule_conflict(
                db,
                provider_id,
                schedule.service_id,
                schedule.day_of_week,
                new_start,
                new_end,
                exclude_schedule_id=schedule_id,
            )
            
            schedule.start_time = new_start
            schedule.end_time = new_end
        
        if slot_duration_minutes is not None:
            if slot_duration_minutes <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Slot duration must be positive",
                )
            schedule.slot_duration_minutes = slot_duration_minutes
        
        if valid_from is not None:
            schedule.valid_from = valid_from
        if valid_until is not None:
            schedule.valid_until = valid_until
        if is_active is not None:
            schedule.is_active = is_active
        
        schedule.updated_at = datetime.utcnow()
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule
    
    async def delete_schedule(self, db: AsyncSession, schedule_id: int, provider_id: int) -> None:
        """Delete a schedule."""
        schedule = await self.get_schedule(db, schedule_id, provider_id)
        await db.delete(schedule)
        await db.commit()
    
    async def generate_slots_from_schedule(
        self,
        db: AsyncSession,
        schedule: ProviderSchedule,
        date: datetime,
    ) -> list[ServiceSlot]:
        """Generate service slots for a specific date based on a schedule."""
        
        # Check if schedule is valid for this date
        if date.date() < schedule.valid_from.date():
            return []
        if schedule.valid_until and date.date() > schedule.valid_until.date():
            return []
        
        # Check if schedule applies to this day
        if schedule.schedule_type == ScheduleType.WEEKLY:
            if date.weekday() != schedule.day_of_week:
                return []
        
        # Generate slots
        slots = []
        current_time = datetime.combine(date.date(), schedule.start_time)
        end_datetime = datetime.combine(date.date(), schedule.end_time)
        
        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=schedule.slot_duration_minutes)
            
            if slot_end > end_datetime:
                break
            
            # Check if slot already exists
            existing = await db.scalar(
                select(ServiceSlot).where(
                    and_(
                        ServiceSlot.service_id == schedule.service_id,
                        ServiceSlot.starts_at == current_time,
                        ServiceSlot.ends_at == slot_end,
                    )
                )
            )
            
            if not existing:
                slot = ServiceSlot(
                    service_id=schedule.service_id,
                    starts_at=current_time,
                    ends_at=slot_end,
                    is_booked=False,
                )
                db.add(slot)
                slots.append(slot)
            
            current_time = slot_end
        
        await db.commit()
        return slots
    
    async def _check_schedule_conflict(
        self,
        db: AsyncSession,
        provider_id: int,
        service_id: Optional[int],
        day_of_week: Optional[int],
        start_time: time,
        end_time: time,
        exclude_schedule_id: Optional[int] = None,
    ) -> None:
        """Check for overlapping schedules."""
        
        # Build base query
        conditions = [
            ProviderSchedule.provider_id == provider_id,
            ProviderSchedule.is_active == True,
        ]
        
        if service_id is not None:
            conditions.append(ProviderSchedule.service_id == service_id)
        
        if day_of_week is not None:
            conditions.append(ProviderSchedule.day_of_week == day_of_week)
        
        if exclude_schedule_id is not None:
            conditions.append(ProviderSchedule.id != exclude_schedule_id)
        
        # Check for time overlap
        # Two schedules overlap if: (start1 < end2) and (start2 < end1)
        time_overlap = and_(
            ProviderSchedule.start_time < end_time,
            ProviderSchedule.end_time > start_time,
        )
        
        conditions.append(time_overlap)
        
        statement = select(ProviderSchedule).where(and_(*conditions))
        result = await db.scalars(statement)
        conflicts = list(result.all())
        
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Schedule conflicts with {len(conflicts)} existing schedule(s)",
            )
