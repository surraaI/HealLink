from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.provider import ProviderType

from app.schemas.patient import PatientResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    patient: Union[PatientResponse, ProviderResponse]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password should have at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password should not exceed 128 characters")
        return v


class UserRegisterData(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone_number: str
    date_of_birth: date | None = None
    gender: str | None = None
    role: Literal["patient"] = "patient"


class DoctorRegisterData(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str | None = None
    phone_number: str
    role: Literal["doctor"] = "doctor"
    license_number: str
    location: str
    license_document: bytes | None = None


class ClinicRegisterData(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str | None = None
    role: Literal["clinic"] = "clinic"
    address: str
    phone_number: str
    license_number: str
    tin_number: str
    license_document: bytes | None = None


class DiagnosticCenterRegisterData(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str | None = None
    role: Literal["diagnostic_center"] = "diagnostic_center"
    address: str
    phone_number: str
    license_number: str
    tin_number: str
    license_document: bytes | None = None


class StaffRegisterData(BaseModel):
    employer_id: int
    employer_type: ProviderType
    email: str
    first_name: str
    last_name: str | None = None
    phone_number: str
    role: Literal["lab assistant", "card_checker"]
    send_invitation: bool | None = None
