from datetime import date, datetime
from typing import Literal

from fastapi import Form, UploadFile, File
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PatientCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["patient"] = "patient"
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    phone_number: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=30)


class PatientLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password should have at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password should not exceed 128 characters")
        return v


class PatientUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    phone_number: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=30)


class PatientUpdateForm(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    profile_picture: UploadFile | None = None

    @classmethod
    def as_form(
        cls,
        email: str | None = Form(None),
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        phone_number: str | None = Form(None),
        date_of_birth: str | None = Form(None),
        gender: str | None = Form(None),
        profile_picture: UploadFile = File(None),
    ) -> "PatientUpdateForm":
        obj = cls(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            date_of_birth=date_of_birth,
            gender=gender,
            profile_picture=profile_picture,
        )
        return obj


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    profile_picture: str | None = None
    role: str = "patient"
    is_active: bool
    is_verified: bool = False
    verification_status: str = "pending"
    created_at: datetime
    updated_at: datetime | None = None
