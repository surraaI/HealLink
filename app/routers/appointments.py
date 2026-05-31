from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, ServiceCatalogResponse
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointments"])
appointment_service = AppointmentService()


@router.get("/services", response_model=list[ServiceCatalogResponse])
async def list_services(
    db: Annotated[AsyncSession, Depends(get_db)],
    service_type: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
) -> list[ServiceCatalogResponse]:
    services = await appointment_service.list_services(db, service_type=service_type, location=location)
    return [ServiceCatalogResponse.model_validate(service) for service in services]


@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    payload: AppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> AppointmentResponse:
    appointment = await appointment_service.create_appointment(db, payload, current_patient)
    return AppointmentResponse.model_validate(appointment)


@router.get("/mine", response_model=list[AppointmentResponse])
async def list_my_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> list[AppointmentResponse]:
    appointments = await appointment_service.list_patient_appointments(db, current_patient.id)
    return [AppointmentResponse.model_validate(appointment) for appointment in appointments]


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> AppointmentResponse:
    appointment = await appointment_service.cancel_appointment(db, appointment_id, current_patient.id)
    return AppointmentResponse.model_validate(appointment)
