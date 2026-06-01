from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    EmailVerificationRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    ResendVerificationRequest,
    TokenResponse,
)
from app.schemas.patient import PatientCreate, PatientLogin
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
async def register_patient(
    payload: PatientCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login_patient(
    payload: PatientLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await auth_service.login(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await auth_service.refresh(db, payload.refresh_token)


@router.post("/logout")
async def logout(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/verify-email")
async def verify_email(
    payload: EmailVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.verify_email(db, payload.token)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.verification_service.resend_verification(db, payload.email)
    return {"message": "If the email exists and is unverified, a new verification code was sent"}


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.request_password_reset(db, payload.email)
    return {"message": "If the email exists, password reset instructions were sent"}


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.reset_password(db, payload.token, payload.new_password)
    return {"message": "Password updated successfully"}
