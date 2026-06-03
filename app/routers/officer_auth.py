from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_officer, get_db
from app.models.officer import Officer
from app.schemas.auth import TokenResponse
from app.schemas.officer import OfficerCreate, OfficerLogin, OfficerResponse, OfficerUpdate
from app.services.super_admin_service import SuperAdminService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/officer", tags=["Officer"])
super_admin_service = SuperAdminService()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: OfficerLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await super_admin_service.officer_login(db, payload.email, payload.password)


@router.get("/profile", response_model=OfficerResponse)
async def get_profile(
    current_officer: Annotated[Officer, Depends(get_current_officer)],
) -> OfficerResponse:
    return OfficerResponse.model_validate(current_officer)


@router.patch("/profile", response_model=OfficerResponse)
async def update_profile(
    payload: OfficerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_officer: Annotated[Officer, Depends(get_current_officer)],
) -> OfficerResponse:
    return await super_admin_service.update_officer_profile(db, current_officer.id, payload)
