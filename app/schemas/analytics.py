from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OverallStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_appointments: int
    completed: int
    cancelled: int
    no_shows: int
    no_show_rate: float
    checked_in: int
    pending: int
    days_scoped: int


class PeakHoursResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hour: int
    appointment_count: int


class DailyTrendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime
    appointment_count: int


class ServiceBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_name: str
    appointment_count: int


class AnalyticsRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
