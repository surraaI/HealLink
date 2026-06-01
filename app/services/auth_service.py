from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.refresh_token import RefreshToken
from app.schemas.auth import TokenResponse
from app.schemas.patient import PatientCreate, PatientResponse
from app.services.account_verification_service import AccountVerificationService
from app.services.patient_service import PatientService

settings = get_settings()


class AuthService:
    def __init__(self) -> None:
        self.patient_service = PatientService()
        self.provider_service = ProviderService()
        self.verification_service = AccountVerificationService()

    async def register(self, db: AsyncSession, payload: PatientCreate) -> TokenResponse:
        existing = await self.patient_service.get_by_email(db, payload.email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        patient = await self.patient_service.create_patient(db, payload)
        await self.verification_service.send_registration_verification(db, patient)
        return await self._issue_token_pair(db, patient)

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        # Try patient login first
        patient = await self.patient_service.authenticate(db, email, password)
        if patient:
            return await self._issue_token_pair(db, patient)
        
        # Try provider login
        provider = await self.provider_service.authenticate(db, email, password)
        if provider:
            if provider.verification_status != "approved":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Provider account is not approved",
                )
            return await self._issue_provider_token_pair(db, provider)
        
        # Neither patient nor provider found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    async def deactivate_patient(self, db: AsyncSession, patient: Patient) -> None:
        await self.patient_service.deactivate_patient(db, patient)

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        patient_id = self._parse_subject(payload.get("sub"))
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        token_record = await db.scalar(statement)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not recognized",
            )
        if token_record.token_hash != hash_token(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token mismatch",
            )
        if token_record.revoked_at is not None or token_record.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            )

        patient = await self.patient_service.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Patient not found",
            )
        if not patient.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        if not patient.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email before logging in",
            )

        token_record.revoked_at = datetime.utcnow()
        db.add(token_record)
        await db.commit()

        return await self._issue_token_pair(db, patient)

    async def verify_email(self, db: AsyncSession, token: str) -> PatientResponse:
        patient = await self.verification_service.verify_email(db, token)
        return PatientResponse.model_validate(patient)

    async def request_password_reset(self, db: AsyncSession, email: str) -> None:
        await self.verification_service.request_password_reset(db, email)

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> PatientResponse:
        patient = await self.verification_service.reset_password(db, token, new_password)
        return PatientResponse.model_validate(patient)

    async def revoke_refresh_token(self, db: AsyncSession, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        token_record = await db.scalar(statement)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not recognized",
            )
        if token_record.token_hash != hash_token(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token mismatch",
            )
        token_record.revoked_at = datetime.utcnow()
        db.add(token_record)
        await db.commit()

    async def get_patient_from_token(self, db: AsyncSession, token: str) -> Patient:
        payload = decode_token(token)
        if not payload or "sub" not in payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        patient_id = self._parse_subject(payload.get("sub"))
        patient = await self.patient_service.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Patient not found",
            )
        if not patient.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        if not patient.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email before logging in",
            )
        return patient

    async def get_provider_from_token(self, db: AsyncSession, token: str) -> Provider:
        payload = decode_token(token)
        if not payload or "sub" not in payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        provider_id = self._parse_subject(payload.get("sub"))
        stmt = select(Provider).where(Provider.id == provider_id)
        provider = await db.scalar(stmt)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provider not found",
            )
        if provider.verification_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provider account is not approved",
            )
        return provider

    async def _issue_token_pair(self, db: AsyncSession, patient: Patient) -> TokenResponse:
        access_token = create_access_token(str(patient.id))
        refresh_jti = str(uuid4())
        refresh_token = create_refresh_token(str(patient.id), jti=refresh_jti)
        refresh_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        token_record = RefreshToken(
            patient_id=patient.id,
            jti=refresh_jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
        db.add(token_record)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            patient=PatientResponse.model_validate(patient),
        )

    async def _issue_provider_token_pair(self, db: AsyncSession, provider: Provider) -> TokenResponse:
        access_token = create_access_token(str(provider.id))
        refresh_jti = str(uuid4())
        refresh_token = create_refresh_token(str(provider.id), jti=refresh_jti)
        refresh_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        token_record = RefreshToken(
            patient_id=None,
            jti=refresh_jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
        db.add(token_record)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            patient=ProviderResponse.model_validate(provider),
        )

    def _parse_subject(self, subject: str | None) -> int:
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        try:
            return int(subject)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            ) from exc
