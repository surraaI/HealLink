from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_db, require_super_admin
from app.models.super_admin import SuperAdmin
from app.schemas.auth import TokenResponse
from app.schemas.officer import OfficerCreate, OfficerResponse
from app.schemas.platform_stats import PlatformStatsResponse
from app.schemas.provider import OfficerProviderResponse
from app.schemas.super_admin import DeactivateRequest, SuperAdminCreate, SuperAdminLogin, SuperAdminResponse
from app.services.platform_stats_service import PlatformStatsService
from app.services.storage_service import generate_signed_url
from app.services.super_admin_service import SuperAdminService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/super-admin", tags=["Super Admin"])
super_admin_service = SuperAdminService()
platform_stats_service = PlatformStatsService()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: SuperAdminLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await super_admin_service.login(db, payload.email, payload.password)


@router.get("/profile", response_model=SuperAdminResponse)
async def get_profile(
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> SuperAdminResponse:
    return SuperAdminResponse.model_validate(current_admin)


# Super Admin Management
@router.post("/admins", response_model=SuperAdminResponse)
async def create_admin(
    payload: SuperAdminCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> SuperAdminResponse:
    return await super_admin_service.create_admin(db, payload, current_admin)


@router.get("/admins", response_model=list[SuperAdminResponse])
async def list_admins(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> list[SuperAdminResponse]:
    return await super_admin_service.list_all(db)


@router.post("/admins/{admin_id}/deactivate", response_model=SuperAdminResponse)
async def deactivate_admin(
    admin_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> SuperAdminResponse:
    return await super_admin_service.deactivate_admin(db, admin_id, current_admin)


@router.post("/admins/{admin_id}/reactivate", response_model=SuperAdminResponse)
async def reactivate_admin(
    admin_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> SuperAdminResponse:
    return await super_admin_service.reactivate_admin(db, admin_id, current_admin)


# Officer Management
@router.post("/officers", response_model=OfficerResponse)
async def create_officer(
    payload: OfficerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> OfficerResponse:
    return await super_admin_service.create_officer(db, payload, current_admin)


@router.get("/officers", response_model=list[OfficerResponse])
async def list_officers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> list[OfficerResponse]:
    return await super_admin_service.list_officers(db)


@router.get("/officers/{officer_id}", response_model=OfficerResponse)
async def get_officer_details(
    officer_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> OfficerResponse:
    return await super_admin_service.get_officer_details(db, officer_id)


@router.post("/officers/{officer_id}/deactivate", response_model=OfficerResponse)
async def deactivate_officer(
    officer_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> OfficerResponse:
    return await super_admin_service.deactivate_officer(db, officer_id, current_admin)


@router.post("/officers/{officer_id}/reactivate", response_model=OfficerResponse)
async def reactivate_officer(
    officer_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> OfficerResponse:
    return await super_admin_service.reactivate_officer(db, officer_id, current_admin)


# Provider Management
@router.get("/providers", response_model=list[OfficerProviderResponse])
async def list_providers(
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    verification_status: Annotated[str | None, Query()] = None,
    provider_type: Annotated[str | None, Query()] = None,
) -> list[OfficerProviderResponse]:
    return await super_admin_service.list_providers(db, verification_status, provider_type)


@router.get("/providers/{provider_id}")
async def get_provider_details(
    provider_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
):
    return await super_admin_service.get_provider_details(db, provider_id)


@router.get("/providers/{provider_id}/document")
async def get_provider_document(
    provider_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
):
    from app.models.provider import Provider
    from sqlalchemy import select
    from fastapi import HTTPException, status

    provider = await db.scalar(select(Provider).where(Provider.id == provider_id))
    if not provider or not provider.license_document_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    signed = generate_signed_url(provider.license_document_url)
    return {"signed_url": signed, "expires_in": 3600}


@router.post("/providers/{provider_id}/deactivate")
async def deactivate_provider(
    provider_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
):
    return await super_admin_service.deactivate_provider(db, provider_id, current_admin)


@router.post("/providers/{provider_id}/reactivate")
async def reactivate_provider(
    provider_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
):
    return await super_admin_service.reactivate_provider(db, provider_id, current_admin)


# Platform Stats
@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[SuperAdmin, Depends(require_super_admin)],
) -> PlatformStatsResponse:
    stats = await platform_stats_service.get_platform_stats(db)
    return PlatformStatsResponse(**stats)
