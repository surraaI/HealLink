from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.models.appointment import Appointment
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


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> dict[str, str]:
    # Check if appointment exists and belongs to current patient
    appointment = await db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_patient.id
        )
    )
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Only allow deletion of cancelled or completed appointments
    if appointment.status not in ["cancelled", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete cancelled or completed appointments"
        )

    # Free up the slot if it exists
    if appointment.slot_id:
        from app.models.provider import ServiceSlot
        slot = await db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
        if slot:
            slot.is_booked = False
            db.add(slot)

    # Delete the appointment
    await db.execute(delete(Appointment).where(Appointment.id == appointment_id))
    await db.commit()
    return {"message": "Appointment deleted successfully"}
