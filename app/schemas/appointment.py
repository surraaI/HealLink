from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ServiceCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    service_type: str
    location: str
    price: Decimal
    duration_minutes: int
    description: str | None
    is_active: bool


class AppointmentCreate(BaseModel):
    service_id: int
    slot_id: int
    note: str | None = Field(default=None, max_length=1000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    service_id: int
    appointment_at: datetime
    status: str
    note: str | None
    created_at: datetime
