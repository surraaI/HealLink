from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProviderVerificationStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pending: int
    approved: int
    rejected: int
    total: int


class ProviderTypeStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor: int
    clinic: int
    diagnostic_center: int
    total: int


class AppointmentStatusStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booked: int
    completed: int
    cancelled: int
    needs_recheck: int
    follow_up_booked: int
    checked_in: int
    total: int


class RevenueStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_revenue: float
    last_30_days_revenue: float


class NewUsersStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    new_patients_last_30_days: int
    new_providers_last_30_days: int


class PlatformStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_patients: int
    total_providers: int
    provider_verification_stats: ProviderVerificationStats
    provider_type_stats: ProviderTypeStats
    appointment_status_stats: AppointmentStatusStats
    revenue_stats: RevenueStats
    new_users_stats: NewUsersStats
