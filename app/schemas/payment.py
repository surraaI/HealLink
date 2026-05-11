from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ChapaInitializeForAppointmentRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, description="Optional: 10 digits like 09xxxxxxxx or 07xxxxxxxx")

    callback_url: str | None = None
    return_url: str | None = None


class ChapaInitializeResponse(BaseModel):
    tx_ref: str
    checkout_url: str


class ChapaVerifyResponse(BaseModel):
    status: str
    tx_ref: str | None = None
    chapa_reference: str | None = None
    amount: str | None = None
    currency: str | None = None
    raw: dict


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    appointment_id: int
    provider: str
    tx_ref: str
    amount: Decimal
    currency: str
    status: str
    checkout_url: str | None
    chapa_reference: str | None

