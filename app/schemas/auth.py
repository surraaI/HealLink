from pydantic import BaseModel

from app.schemas.patient import PatientResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    patient: PatientResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str
