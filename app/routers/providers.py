from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.appointment import AppointmentResponse, ServiceCatalogResponse
from app.schemas.provider import (
    BookRecheckRequest,
    NeedsRecheckRequest,
    ProviderCreate,
    ProviderResponse,
    ProviderServiceCreate,
    ServiceSlotCreate,
    ServiceSlotResponse,
)
from app.services.appointment_provider_service import AppointmentProviderService
from app.services.notification_service import NotificationService
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["Providers"])
provider_service = ProviderService()
appointment_provider_service = AppointmentProviderService()
notification_service = NotificationService()


@router.get("", response_model=list[ProviderResponse])
def list_providers(
    db: Annotated[Session, Depends(get_db)],
    provider_type: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
) -> list[ProviderResponse]:
    providers = provider_service.list_providers(db, provider_type=provider_type, location=location)
    return [ProviderResponse.model_validate(item) for item in providers]


@router.post("", response_model=ProviderResponse)
def register_provider(
    payload: ProviderCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderResponse:
    provider = provider_service.create_provider(db, payload)
    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/services", response_model=ServiceCatalogResponse)
def create_provider_service(
    provider_id: int,
    payload: ProviderServiceCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceCatalogResponse:
    service = provider_service.create_service(db, provider_id, payload)
    return ServiceCatalogResponse.model_validate(service)


@router.post("/services/{service_id}/slots", response_model=ServiceSlotResponse)
def create_service_slot(
    service_id: int,
    payload: ServiceSlotCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceSlotResponse:
    slot = provider_service.create_service_slot(db, service_id, payload)
    return ServiceSlotResponse.model_validate(slot)


@router.get("/services/{service_id}/slots", response_model=list[ServiceSlotResponse])
def list_service_slots(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    only_available: bool = True,
) -> list[ServiceSlotResponse]:
    slots = provider_service.list_service_slots(db, service_id=service_id, only_available=only_available)
    return [ServiceSlotResponse.model_validate(item) for item in slots]


@router.post("/{provider_id}/appointments/{appointment_id}/complete", response_model=AppointmentResponse)
def provider_mark_visit_completed(
    provider_id: int,
    appointment_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    appointment = appointment_provider_service.mark_completed(db, provider_id, appointment_id)
    patient = db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
    notification_service.stage_patient_event(
        db,
        patient_id=appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Visit completed",
        body="Your healthcare provider marked this appointment as completed.",
        appointment_id=appointment.id,
    )
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)


@router.post("/{provider_id}/appointments/{appointment_id}/needs-recheck", response_model=AppointmentResponse)
def provider_mark_needs_recheck(
    provider_id: int,
    appointment_id: int,
    payload: NeedsRecheckRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    appointment = appointment_provider_service.mark_needs_recheck(
        db, provider_id, appointment_id, payload.reason
    )
    patient = db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
    reason_text = (
        f" Reason: {appointment.provider_recheck_reason}"
        if appointment.provider_recheck_reason
        else ""
    )
    notification_service.stage_patient_event(
        db,
        patient_id=appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Follow-up visit needed",
        body=f"Your provider indicated a recheck or follow-up is needed.{reason_text}",
        appointment_id=appointment.id,
    )
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)


@router.post("/{provider_id}/appointments/{appointment_id}/book-recheck", response_model=AppointmentResponse)
def provider_book_recheck_visit(
    provider_id: int,
    appointment_id: int,
    payload: BookRecheckRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    new_appointment, _original = appointment_provider_service.book_follow_up(
        db, provider_id, appointment_id, payload.slot_id
    )
    patient = db.scalar(select(Patient).where(Patient.id == new_appointment.patient_id))
    notification_service.stage_patient_event(
        db,
        patient_id=new_appointment.patient_id,
        patient_email=patient.email if patient else None,
        title="Follow-up appointment scheduled",
        body=f"A recheck appointment was booked for you on {new_appointment.appointment_at}.",
        appointment_id=new_appointment.id,
    )
    db.commit()
    db.refresh(new_appointment)
    return AppointmentResponse.model_validate(new_appointment)
