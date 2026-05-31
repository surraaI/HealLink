from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import Form, UploadFile, File
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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


class ProviderRegisterForm(BaseModel):
    name: str
    provider_type: str
    email: EmailStr
    phone: str | None = None
    location: str
    description: str | None = None

    # helper to be used in FastAPI endpoint as a dependency
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        provider_type: str = Form(...),
        email: EmailStr = Form(...),
        phone: str | None = Form(None),
        location: str = Form(...),
        description: str | None = Form(None),
        license_file: UploadFile = File(...),
    ) -> "ProviderRegisterForm":
        obj = cls(name=name, provider_type=provider_type, email=email, phone=phone, location=location, description=description)
        # attach file for router to receive
        setattr(obj, "license_file", license_file)
        return obj


class ProviderPublicResponse(ProviderResponse):
    verification_status: str


class AdminProviderResponse(ProviderPublicResponse):
    license_document_url: str | None
    rejection_reason: str | None


class VerifyProviderRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = None

    @model_validator(mode="after")
    def check_reason(self):
        if self.action == "reject" and not self.reason:
            raise ValueError("reason is required when rejecting a provider")
        return self


class AdminStatsResponse(BaseModel):
    pending: int
    approved: int
    rejected: int
    total: int


class SignedDocumentResponse(BaseModel):
    signed_url: str
    expires_in: int


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


class NeedsRecheckRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class BookRecheckRequest(BaseModel):
    slot_id: int
