from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientResponse, PatientUpdate
from app.services.account_verification_service import AccountVerificationService
from app.services.auth_service import AuthService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])
patient_service = PatientService()
verification_service = AccountVerificationService()
auth_service = AuthService()


@router.get("/me", response_model=PatientResponse)
async def get_my_profile(
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> PatientResponse:
    return PatientResponse.model_validate(current_patient)


@router.patch("/me", response_model=PatientResponse)
async def update_my_profile(
    payload: PatientUpdate,
    current_patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    updated_patient, email_changed = await patient_service.update_patient(db, current_patient, payload)
    if email_changed:
        await verification_service.request_email_change(db, updated_patient, email_changed)
    return PatientResponse.model_validate(updated_patient)


@router.delete("/me")
async def delete_my_account(
    current_patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.deactivate_patient(db, current_patient)
    return {"message": "Account deleted successfully"}
