from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SuperAdminLogin(BaseModel):
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


class SuperAdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password should have at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password should not exceed 128 characters")
        return v


class SuperAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class SuperAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class DeactivateRequest(BaseModel):
    action: Literal["deactivate", "reactivate"]
