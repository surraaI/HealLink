from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProviderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    provider_type: str
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    location: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    email: EmailStr
    phone: str | None
    location: str
    description: str | None
    created_at: datetime


class ProviderServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    service_type: str = Field(min_length=2, max_length=50)
    location: str = Field(min_length=2, max_length=255)
    price: Decimal
    duration_minutes: int = Field(gt=0, le=480)
    description: str | None = Field(default=None, max_length=1000)


class ServiceSlotCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime


class ServiceSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    starts_at: datetime
    ends_at: datetime
    is_booked: bool
