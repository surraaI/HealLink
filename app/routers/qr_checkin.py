from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient, get_current_provider
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.qr_checkin import QRCheckin
from app.schemas.qr_checkin import QRCheckinResponse, VerifyCheckinRequest, VerifyCheckinResponse
from app.services.qr_checkin_service import QRCheckinService

router = APIRouter(prefix="/qr", tags=["QR Check-in"])
qr_checkin_service = QRCheckinService()


@router.get("/appointments/{appointment_id}", response_model=QRCheckinResponse)
async def get_qr_for_appointment(
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> QRCheckinResponse:
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

    qr_checkin = await qr_checkin_service.get_checkin_by_appointment(db, appointment_id)
    if not qr_checkin:
        qr_checkin = await qr_checkin_service.generate_checkin(db, appointment_id)

    return QRCheckinResponse.model_validate(qr_checkin)


@router.post("/verify", response_model=VerifyCheckinResponse)
async def verify_checkin(
    payload: VerifyCheckinRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> VerifyCheckinResponse:
    from fastapi import HTTPException, status

    qr_checkin = await qr_checkin_service.verify_and_checkin(
        db, payload.card_number, current_provider.id
    )

    appointment = await db.scalar(
        select(Appointment).where(Appointment.id == qr_checkin.appointment_id)
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    from app.models.appointment import ServiceCatalog
    from app.models.patient import Patient

    service = await db.scalar(
        select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id)
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    patient = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"

    return VerifyCheckinResponse(
        appointment_id=appointment.id,
        patient_name=patient_name,
        service_name=service.name,
        checked_in_at=qr_checkin.used_at,
        provider_id=current_provider.id,
    )
