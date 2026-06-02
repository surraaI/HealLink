from typing import Annotated
import logging

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_provider
from app.db.session import get_db
from app.models.patient import Patient
from app.models.provider import Provider
from app.schemas.provider import (
    BookRecheckRequest,
    NeedsRecheckRequest,
    ProviderCreate,
    ProviderRegisterForm,
    ProviderResponse,
    ProviderServiceCreate,
    ServiceSlotCreate,
    ServiceSlotResponse,
)
from app.schemas.appointment import AppointmentResponse, ServiceCatalogResponse
from app.services.appointment_provider_service import AppointmentProviderService
from app.services.notification_service import NotificationService
from app.services.provider_service import ProviderService, register_provider_with_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/providers", tags=["Providers"])
provider_service = ProviderService()
appointment_provider_service = AppointmentProviderService()
notification_service = NotificationService()


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_type: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
) -> list[ProviderResponse]:
    providers = await provider_service.list_providers(db, provider_type=provider_type, location=location)
    return [ProviderResponse.model_validate(item) for item in providers]


@router.post("", response_model=ProviderResponse)
async def register_provider(
    form: Annotated[ProviderRegisterForm, Depends(ProviderRegisterForm.as_form)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderResponse:
    # license_file is attached to the form by as_form
    license_file: UploadFile = getattr(form, "license_file")
    provider = await register_provider_with_document(db, form, license_file)
    return ProviderResponse.model_validate(provider)


@router.post("/services", response_model=ServiceCatalogResponse)
async def create_provider_service(
    payload: ProviderServiceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_provider: Annotated[Provider, Depends(get_current_provider)],
) -> ServiceCatalogResponse:
    logger.info(f"Creating service for provider {current_provider.id} with payload: {payload}")
    service = await provider_service.create_service(db, current_provider.id, payload)
    return ServiceCatalogResponse.model_validate(service)


@router.post("/services/{service_id}/slots", response_model=ServiceSlotResponse)
async def create_service_slot(
    service_id: int,
    payload: ServiceSlotCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceSlotResponse:
    slot = await provider_service.create_service_slot(db, service_id, payload)
    return ServiceSlotResponse.model_validate(slot)


@router.get("/services/{service_id}/slots", response_model=list[ServiceSlotResponse])
async def list_service_slots(
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    only_available: bool = True,
) -> list[ServiceSlotResponse]:
    slots = await provider_service.list_service_slots(db, service_id=service_id, only_available=only_available)
    return [ServiceSlotResponse.model_validate(item) for item in slots]


@router.post("/{provider_id}/appointments/{appointment_id}/complete", response_model=AppointmentResponse)
async def provider_mark_visit_completed(
    provider_id: int,
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    appointment = await appointment_provider_service.mark_completed(db, provider_id, appointment_id)
    patient = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
    await notification_service.stage_patient_event(
        db,
        patient_id=appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Visit completed",
        body="Your healthcare provider marked this appointment as completed.",
        appointment_id=appointment.id,
    )
    await db.commit()
    await db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)


@router.post("/{provider_id}/appointments/{appointment_id}/needs-recheck", response_model=AppointmentResponse)
async def provider_mark_needs_recheck(
    provider_id: int,
    appointment_id: int,
    payload: NeedsRecheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    appointment = await appointment_provider_service.mark_needs_recheck(
        db, provider_id, appointment_id, payload.reason
    )
    patient = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
    reason_text = (
        f" Reason: {appointment.provider_recheck_reason}"
        if appointment.provider_recheck_reason
        else ""
    )
    await notification_service.stage_patient_event(
        db,
        patient_id=appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Follow-up visit needed",
        body=f"Your provider indicated a recheck or follow-up is needed.{reason_text}",
        appointment_id=appointment.id,
    )
    await db.commit()
    await db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)


@router.post("/{provider_id}/appointments/{appointment_id}/book-recheck", response_model=AppointmentResponse)
async def provider_book_recheck_visit(
    provider_id: int,
    appointment_id: int,
    payload: BookRecheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    new_appointment, _original = await appointment_provider_service.book_follow_up(
        db, provider_id, appointment_id, payload.slot_id
    )
    patient = await db.scalar(select(Patient).where(Patient.id == new_appointment.patient_id))
    await notification_service.stage_patient_event(
        db,
        patient_id=new_appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Follow-up appointment scheduled",
        body=f"A recheck appointment was booked for you on {new_appointment.appointment_at}.",
        appointment_id=new_appointment.id,
    )
    await db.commit()
    await db.refresh(new_appointment)
    return AppointmentResponse.model_validate(new_appointment)


@router.post("/{provider_id}/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def provider_reschedule_appointment(
    provider_id: int,
    appointment_id: int,
    payload: BookRecheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    """Reschedule an appointment to a new slot with QR code reactivation."""
    appointment = await appointment_provider_service.reschedule_appointment(
        db, provider_id, appointment_id, payload.slot_id
    )
    return AppointmentResponse.model_validate(appointment)

