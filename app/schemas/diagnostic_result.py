from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from typing import Literal


class DiagnosticResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    status: str
    updated_at: datetime


class DiagnosticResultProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    status: str
    updated_at: datetime
    updated_by_provider_id: int | None
    created_at: datetime


class UpdateStatusRequest(BaseModel):
    status: Literal["pending", "ready", "collected"]
