from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient, get_current_provider
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.provider import Provider
from app.schemas.diagnostic_result import (
    DiagnosticResultProviderResponse,
    DiagnosticResultResponse,
    UpdateStatusRequest,
)
from app.services.diagnostic_result_service import DiagnosticResultService

router = APIRouter(prefix="/diagnostic-results", tags=["Diagnostic Results"])
diagnostic_result_service = DiagnosticResultService()


@router.get("/appointments/{appointment_id}", response_model=DiagnosticResultResponse)
async def get_result_for_appointment(
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> DiagnosticResultResponse:
    appointment = await db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if not appointment:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if appointment.patient_id != current_patient.id:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this appointment",
        )

    result = await diagnostic_result_service.get_or_create_result(db, appointment_id)
    return DiagnosticResultResponse.model_validate(result)


@router.put("/appointments/{appointment_id}/status", response_model=DiagnosticResultProviderResponse)
async def update_result_status(
    appointment_id: int,
    payload: UpdateStatusRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> DiagnosticResultProviderResponse:
    from app.models.appointment import ServiceCatalog

    appointment = await db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if not appointment:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    service = await db.scalar(
        select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id)
    )
    if not service or service.provider_id != current_provider.id:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update this appointment's result status",
        )

    result = await diagnostic_result_service.update_status(
        db, appointment_id, payload.status, current_provider.id
    )
    return DiagnosticResultProviderResponse.model_validate(result)


@router.get("/mine", response_model=list[DiagnosticResultProviderResponse])
async def get_my_results(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> list[DiagnosticResultProviderResponse]:
    results = await diagnostic_result_service.get_results_for_provider(db, current_provider.id)
    return [DiagnosticResultProviderResponse.model_validate(result) for result in results]
