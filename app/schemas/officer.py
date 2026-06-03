from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OfficerLogin(BaseModel):
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


class OfficerCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    badge_number: str = Field(min_length=2, max_length=50)
    department: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password should have at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password should not exceed 128 characters")
        return v


class OfficerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    badge_number: str
    department: str
    is_active: bool
    created_at: datetime


class OfficerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    department: str | None = Field(default=None, min_length=2, max_length=255)
