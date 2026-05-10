from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PatientLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
