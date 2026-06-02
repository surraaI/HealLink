from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import Form, UploadFile, File
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ProviderCreate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
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

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password should have at least 8 characters")
            if len(v) > 128:
                raise ValueError("Password should not exceed 128 characters")
        return v

    @model_validator(mode="after")
    def normalize_fields(self):
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
    profile_picture: str | None = None
    is_verified: bool = False
    verification_status: str = "pending"
    created_at: datetime


class ProviderRegisterForm(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str | None = None
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
    license_file: UploadFile | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password should have at least 8 characters")
            if len(v) > 128:
                raise ValueError("Password should not exceed 128 characters")
        return v

    # helper to be used in FastAPI endpoint as a dependency
    @classmethod
    def as_form(
        cls,
        provider_type: str = Form(...),
        email: EmailStr = Form(...),
        password: str | None = Form(None),
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
            license_file=license_file,
        )
        return obj


class ProviderPublicResponse(ProviderResponse):
    verification_status: str


class OfficerProviderResponse(ProviderPublicResponse):
    license_document_url: str | None
    rejection_reason: str | None
    verified_by: int | None
    verified_at: datetime | None


class VerifyProviderRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = None

    @model_validator(mode="after")
    def check_reason(self):
        if self.action == "reject" and not self.reason:
            raise ValueError("reason is required when rejecting a provider")
        return self


class OfficerStatsResponse(BaseModel):
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
    location: str = Field(max_length=255)
    price: Decimal
    duration_minutes: int = Field(gt=0, le=480)
    description: str | None = Field(default=None, max_length=1000)


class ProviderServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    service_type: str | None = Field(default=None, min_length=2, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    price: Decimal | None = Field(default=None)
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    description: str | None = Field(default=None, max_length=1000)


class ProviderUpdateForm(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str | None = None
    phone: str | None = None
    specialization: str | None = None
    location: str | None = None
    address: str | None = None
    description: str | None = None
    profile_picture: UploadFile | None = None

    @classmethod
    def as_form(
        cls,
        name: str | None = Form(None),
        phone: str | None = Form(None),
        specialization: str | None = Form(None),
        location: str | None = Form(None),
        address: str | None = Form(None),
        description: str | None = Form(None),
        profile_picture: UploadFile = File(None),
    ) -> "ProviderUpdateForm":
        obj = cls(
            name=name,
            phone=phone,
            specialization=specialization,
            location=location,
            address=address,
            description=description,
            profile_picture=profile_picture,
        )
        return obj


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
