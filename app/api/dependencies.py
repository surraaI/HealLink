from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.officer import Officer
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.super_admin import SuperAdmin
from app.services.auth_service import AuthService
from app.services.super_admin_service import SuperAdminService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()
super_admin_service = SuperAdminService()


async def get_current_patient(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Patient:
    try:
        return await auth_service.get_patient_from_token(db, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc


async def get_current_super_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuperAdmin:
    payload = decode_token(token)
    if not payload or "sub" not in payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin token required",
        )
    admin_id = int(payload["sub"])
    admin = await super_admin_service.get_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Super admin not found",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )
    return admin


async def get_current_officer(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Officer:
    payload = decode_token(token)
    if not payload or "sub" not in payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("role") != "officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer token required",
        )
    officer_id = int(payload["sub"])
    from app.services.super_admin_service import SuperAdminService
    service = SuperAdminService()
    officer = await service.get_officer_by_id(db, officer_id)
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Officer not found",
        )
    if not officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )
    return officer


async def require_super_admin(current_admin: Annotated[SuperAdmin, Depends(get_current_super_admin)]) -> SuperAdmin:
    return current_admin


async def get_current_provider(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Provider:
    try:
        return await auth_service.get_provider_from_token(db, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc
