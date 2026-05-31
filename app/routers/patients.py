from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_patient
from app.models.patient import Patient
from app.schemas.patient import PatientResponse

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/me", response_model=PatientResponse)
async def get_my_profile(
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> PatientResponse:
    return PatientResponse.model_validate(current_patient)
