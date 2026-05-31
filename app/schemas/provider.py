from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import Form, UploadFile, File
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ProviderCreate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    provider_type: str
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)
    phone_number: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    address: str | None = Field(default=None, min_length=2, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    license_number: str | None = Field(default=None, max_length=100)
    tin_number: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def normalize_fields(self):
        if not self.name and self.full_name:
            self.name = self.full_name
        if not self.location and self.address:
            self.location = self.address
        if not self.phone and self.phone_number:
            self.phone = self.phone_number
        return self


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    email: EmailStr
    phone: str | None
    specialization: str | None = None
    license_number: str | None = None
    tin_number: str | None = None
    location: str
    address: str | None = None
    description: str | None
    created_at: datetime


class ProviderRegisterForm(BaseModel):
    name: str | None = None
    full_name: str | None = None
    provider_type: str
    email: EmailStr
    password: str | None = None
    phone: str | None = None
    phone_number: str | None = None
    location: str | None = None
    address: str | None = None
    specialization: str | None = None
    license_number: str | None = None
    tin_number: str | None = None
    description: str | None = None
    role: Literal["doctor", "clinic", "diagnostic_center"] | None = None

    # helper to be used in FastAPI endpoint as a dependency
    @classmethod
    def as_form(
        cls,
        provider_type: str = Form(...),
        email: EmailStr = Form(...),
        password: str | None = Form(None),
        full_name: str | None = Form(None),
        name: str | None = Form(None),
        phone_number: str | None = Form(None),
        phone: str | None = Form(None),
        location: str | None = Form(None),
        address: str | None = Form(None),
        specialization: str | None = Form(None),
        license_number: str | None = Form(None),
        tin_number: str | None = Form(None),
        description: str | None = Form(None),
        role: str | None = Form(None),
        license_file: UploadFile = File(...),
    ) -> "ProviderRegisterForm":
        obj = cls(
            name=name,
            full_name=full_name,
            provider_type=provider_type,
            email=email,
            password=password,
            phone=phone,
            phone_number=phone_number,
            location=location,
            address=address,
            specialization=specialization,
            license_number=license_number,
            tin_number=tin_number,
            description=description,
            role=role,
        )
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
