from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QRCheckinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    card_number: str
    qr_image_b64: str
    status: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    used_by_provider_id: int | None
    is_expired: bool = Field(default=False)

    @field_validator("is_expired", mode="before")
    @classmethod
    def compute_is_expired(cls, v: bool, info) -> bool:
        if "expires_at" in info.data:
            return info.data["expires_at"] < datetime.now(timezone.utc)
        return v


class VerifyCheckinRequest(BaseModel):
    card_number: str

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped.isdigit() or len(stripped) != 6:
            raise ValueError("Card number must be exactly 6 digits")
        return stripped


class VerifyCheckinResponse(BaseModel):
    appointment_id: int
    patient_name: str
    service_name: str
    checked_in_at: datetime
    provider_id: int
