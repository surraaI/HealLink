from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import require_super_admin
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.provider import OfficerProviderResponse, VerifyProviderRequest, OfficerStatsResponse, SignedDocumentResponse
from app.services.provider_service import get_providers_by_status, verify_provider, get_provider_stats
from app.services.storage_service import generate_signed_url
from app.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.provider import Provider
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/officer", tags=["Officer"])
auth_service = AuthService()


@router.get("/providers", response_model=list[OfficerProviderResponse])
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query()] = None,
    _officer=Depends(require_super_admin),
) -> list[OfficerProviderResponse]:
    items = await get_providers_by_status(db, status)
    return [OfficerProviderResponse.model_validate(i) for i in items]


@router.get("/providers/{provider_id}/document", response_model=SignedDocumentResponse)
async def get_provider_document(
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: Annotated[int, Path(...)],
    _officer=Depends(require_super_admin),
):
    provider = await db.scalar(select(Provider).where(Provider.id == provider_id))
    if not provider or not provider.license_document_url:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    signed = generate_signed_url(provider.license_document_url)
    return SignedDocumentResponse(signed_url=signed, expires_in=3600)


@router.post("/providers/{provider_id}/verify", response_model=OfficerProviderResponse)
async def post_verify_provider(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: VerifyProviderRequest,
    provider_id: Annotated[int, Path(...)],
    officer=Depends(require_super_admin),
):
    officer_id = getattr(officer, "id", None)
    prov = await verify_provider(db, provider_id, payload.action, payload.reason, officer_id)
    return OfficerProviderResponse.model_validate(prov)


@router.get("/stats", response_model=OfficerStatsResponse)
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _officer=Depends(require_super_admin),
):
    stats = await get_provider_stats(db)
    return OfficerStatsResponse.model_validate(stats)


@router.delete("/patients/{patient_id}")
async def delete_patient(
    db: Annotated[AsyncSession, Depends(get_db)],
    patient_id: Annotated[int, Path(...)],
    _officer=Depends(require_super_admin),
) -> dict[str, str]:
    patient = await db.scalar(select(Patient).where(Patient.id == patient_id))
    if not patient:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    await auth_service.deactivate_patient(db, patient)
    return {"message": "Patient deleted successfully"}
