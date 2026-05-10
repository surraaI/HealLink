from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import RefreshTokenRequest, TokenResponse
from app.schemas.patient import PatientCreate, PatientLogin
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
def register_patient(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
def login_patient(
    payload: PatientLogin,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return auth_service.login(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return auth_service.refresh(db, payload.refresh_token)


@router.post("/logout")
def logout(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    auth_service.revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out successfully"}
