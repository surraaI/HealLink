from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientResponse, PatientUpdate, PatientUpdateForm
from app.services.account_verification_service import AccountVerificationService
from app.services.auth_service import AuthService
from app.services.patient_service import PatientService
from app.services.storage_service import upload_profile_picture

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


@router.patch("/me/profile", response_model=PatientResponse)
async def update_my_profile_with_picture(
    form: Annotated[PatientUpdateForm, Depends(PatientUpdateForm.as_form)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    # Handle profile picture upload if provided
    profile_picture_url = None
    if form.profile_picture:
        profile_picture_url = await upload_profile_picture(form.profile_picture, "patient", current_patient.id)

    # Update patient fields
    if form.first_name is not None:
        current_patient.first_name = form.first_name
    if form.last_name is not None:
        current_patient.last_name = form.last_name
    if form.phone_number is not None:
        current_patient.phone_number = form.phone_number
    if form.gender is not None:
        current_patient.gender = form.gender
    if profile_picture_url is not None:
        current_patient.profile_picture = profile_picture_url

    await db.commit()
    await db.refresh(current_patient)
    return PatientResponse.model_validate(current_patient)


@router.delete("/me")
async def delete_my_account(
    current_patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.deactivate_patient(db, current_patient)
    return {"message": "Account deleted successfully"}
