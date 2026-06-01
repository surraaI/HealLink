from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.provider_schedule import ScheduleType


class ScheduleCreate(BaseModel):
    service_id: Optional[int] = Field(default=None)
    schedule_type: ScheduleType
    day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(gt=0, le=480)
    valid_from: datetime
    valid_until: Optional[datetime] = Field(default=None)


class ScheduleUpdate(BaseModel):
    start_time: Optional[time] = Field(default=None)
    end_time: Optional[time] = Field(default=None)
    slot_duration_minutes: Optional[int] = Field(default=None, gt=0, le=480)
    valid_from: Optional[datetime] = Field(default=None)
    valid_until: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    service_id: Optional[int]
    schedule_type: str
    day_of_week: Optional[int]
    start_time: time
    end_time: time
    slot_duration_minutes: int
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GenerateSlotsRequest(BaseModel):
    date: datetime


class SlotGenerationResponse(BaseModel):
    message: str
    slots_created: int
