from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.officer import Officer
from app.models.provider import Provider
from app.models.refresh_token import RefreshToken
from app.models.super_admin import SuperAdmin
from app.schemas.auth import TokenResponse
from app.schemas.officer import OfficerCreate, OfficerResponse, OfficerUpdate
from app.schemas.super_admin import SuperAdminCreate, SuperAdminResponse, SuperAdminUpdate

settings = get_settings()


class SuperAdminService:
    async def authenticate(self, db: AsyncSession, email: str, password: str) -> SuperAdmin:
        stmt = select(SuperAdmin).where(SuperAdmin.email == email.lower())
        admin = await db.scalar(stmt)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        if not verify_password(password, admin.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return admin

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        admin = await self.authenticate(db, email, password)
        return await self._issue_token_pair(db, admin)

    async def authenticate_officer(self, db: AsyncSession, email: str, password: str) -> Officer:
        officer = await self.get_officer_by_email(db, email.lower())
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not officer.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        if not verify_password(password, officer.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return officer

    async def officer_login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        officer = await self.authenticate_officer(db, email, password)
        return await self._issue_officer_token_pair(db, officer)

    async def create_admin(
        self, db: AsyncSession, payload: SuperAdminCreate, created_by: SuperAdmin
    ) -> SuperAdminResponse:
        existing = await self.get_by_email(db, payload.email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        admin = SuperAdmin(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return SuperAdminResponse.model_validate(admin)

    async def get_by_email(self, db: AsyncSession, email: str) -> SuperAdmin | None:
        stmt = select(SuperAdmin).where(SuperAdmin.email == email.lower())
        return await db.scalar(stmt)

    async def get_by_id(self, db: AsyncSession, admin_id: int) -> SuperAdmin | None:
        stmt = select(SuperAdmin).where(SuperAdmin.id == admin_id)
        return await db.scalar(stmt)

    async def list_all(self, db: AsyncSession) -> list[SuperAdminResponse]:
        stmt = select(SuperAdmin).order_by(SuperAdmin.created_at.desc())
        result = await db.execute(stmt)
        admins = result.scalars().all()
        return [SuperAdminResponse.model_validate(admin) for admin in admins]

    async def deactivate_admin(
        self, db: AsyncSession, admin_id: int, current_admin: SuperAdmin
    ) -> SuperAdminResponse:
        if admin_id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself",
            )
        admin = await self.get_by_id(db, admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Super Admin not found",
            )
        admin.is_active = False
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return SuperAdminResponse.model_validate(admin)

    async def reactivate_admin(
        self, db: AsyncSession, admin_id: int, current_admin: SuperAdmin
    ) -> SuperAdminResponse:
        if admin_id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reactivate yourself",
            )
        admin = await self.get_by_id(db, admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Super Admin not found",
            )
        admin.is_active = True
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return SuperAdminResponse.model_validate(admin)

    async def update_admin_profile(
        self, db: AsyncSession, admin_id: int, payload: SuperAdminUpdate
    ) -> SuperAdminResponse:
        admin = await self.get_by_id(db, admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Super Admin not found",
            )
        if payload.full_name is not None:
            admin.full_name = payload.full_name
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return SuperAdminResponse.model_validate(admin)

    async def create_officer(
        self, db: AsyncSession, payload: OfficerCreate, created_by: SuperAdmin
    ) -> OfficerResponse:
        existing = await self.get_officer_by_email(db, payload.email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        existing_badge = await self.get_officer_by_badge(db, payload.badge_number)
        if existing_badge:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Badge number is already registered",
            )
        officer = Officer(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            badge_number=payload.badge_number,
            department=payload.department,
            is_active=True,
        )
        db.add(officer)
        await db.commit()
        await db.refresh(officer)
        return OfficerResponse.model_validate(officer)

    async def get_officer_by_email(self, db: AsyncSession, email: str) -> Officer | None:
        stmt = select(Officer).where(Officer.email == email.lower())
        return await db.scalar(stmt)

    async def get_officer_by_badge(self, db: AsyncSession, badge_number: str) -> Officer | None:
        stmt = select(Officer).where(Officer.badge_number == badge_number)
        return await db.scalar(stmt)

    async def get_officer_by_id(self, db: AsyncSession, officer_id: int) -> Officer | None:
        stmt = select(Officer).where(Officer.id == officer_id)
        return await db.scalar(stmt)

    async def list_officers(self, db: AsyncSession) -> list[OfficerResponse]:
        stmt = select(Officer).order_by(Officer.created_at.desc())
        result = await db.execute(stmt)
        officers = result.scalars().all()
        return [OfficerResponse.model_validate(officer) for officer in officers]

    async def get_officer_details(self, db: AsyncSession, officer_id: int) -> OfficerResponse:
        officer = await self.get_officer_by_id(db, officer_id)
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Officer not found",
            )
        return OfficerResponse.model_validate(officer)

    async def deactivate_officer(
        self, db: AsyncSession, officer_id: int, current_admin: SuperAdmin
    ) -> OfficerResponse:
        officer = await self.get_officer_by_id(db, officer_id)
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Officer not found",
            )
        officer.is_active = False
        db.add(officer)
        await db.commit()
        await db.refresh(officer)
        return OfficerResponse.model_validate(officer)

    async def reactivate_officer(
        self, db: AsyncSession, officer_id: int, current_admin: SuperAdmin
    ) -> OfficerResponse:
        officer = await self.get_officer_by_id(db, officer_id)
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Officer not found",
            )
        officer.is_active = True
        db.add(officer)
        await db.commit()
        await db.refresh(officer)
        return OfficerResponse.model_validate(officer)

    async def update_officer_profile(
        self, db: AsyncSession, officer_id: int, payload: OfficerUpdate
    ) -> OfficerResponse:
        officer = await self.get_officer_by_id(db, officer_id)
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Officer not found",
            )
        if payload.full_name is not None:
            officer.full_name = payload.full_name
        if payload.department is not None:
            officer.department = payload.department
        db.add(officer)
        await db.commit()
        await db.refresh(officer)
        return OfficerResponse.model_validate(officer)

    async def list_providers(
        self,
        db: AsyncSession,
        verification_status: str | None = None,
        provider_type: str | None = None,
    ) -> list:
        stmt = select(Provider)
        if verification_status and verification_status != "undefined":
            stmt = stmt.where(Provider.verification_status == verification_status)
        if provider_type and provider_type != "undefined" and provider_type != "UNDEFINED":
            stmt = stmt.where(Provider.provider_type == provider_type.upper())
        stmt = stmt.order_by(Provider.created_at.desc())
        result = await db.execute(stmt)
        providers = result.scalars().all()
        from app.schemas.provider import OfficerProviderResponse
        return [OfficerProviderResponse.model_validate(p) for p in providers]

    async def get_provider_details(self, db: AsyncSession, provider_id: int) -> dict:
        stmt = select(Provider).where(Provider.id == provider_id)
        provider = await db.scalar(stmt)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        from app.schemas.provider import OfficerProviderResponse
        return OfficerProviderResponse.model_validate(provider).model_dump()

    async def deactivate_provider(
        self, db: AsyncSession, provider_id: int, current_admin: SuperAdmin
    ) -> dict:
        stmt = select(Provider).where(Provider.id == provider_id)
        provider = await db.scalar(stmt)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        provider.is_verified = False
        provider.verification_status = "rejected"
        provider.rejection_reason = "Deactivated by super admin"
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        from app.schemas.provider import OfficerProviderResponse
        return OfficerProviderResponse.model_validate(provider).model_dump()

    async def reactivate_provider(
        self, db: AsyncSession, provider_id: int, current_admin: SuperAdmin
    ) -> dict:
        stmt = select(Provider).where(Provider.id == provider_id)
        provider = await db.scalar(stmt)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        provider.is_verified = True
        provider.verification_status = "approved"
        provider.rejection_reason = None
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        from app.schemas.provider import OfficerProviderResponse
        return OfficerProviderResponse.model_validate(provider).model_dump()

    async def _issue_token_pair(self, db: AsyncSession, admin: SuperAdmin) -> TokenResponse:
        access_token = create_access_token(str(admin.id), role="super_admin")
        refresh_jti = str(uuid4())
        refresh_token = create_refresh_token(str(admin.id), jti=refresh_jti, role="super_admin")
        refresh_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        token_record = RefreshToken(
            patient_id=None,
            provider_id=None,
            super_admin_id=admin.id,
            jti=refresh_jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
        db.add(token_record)
        await db.commit()

        from app.schemas.super_admin import SuperAdminResponse
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            patient=SuperAdminResponse.model_validate(admin),
        )

    async def _issue_officer_token_pair(self, db: AsyncSession, officer: Officer) -> TokenResponse:
        access_token = create_access_token(str(officer.id), role="officer")
        refresh_jti = str(uuid4())
        refresh_token = create_refresh_token(str(officer.id), jti=refresh_jti, role="officer")
        refresh_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        token_record = RefreshToken(
            patient_id=None,
            provider_id=None,
            super_admin_id=None,
            officer_id=officer.id,
            jti=refresh_jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
        db.add(token_record)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            patient=OfficerResponse.model_validate(officer),
        )
