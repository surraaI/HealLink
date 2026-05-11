from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.payment import (
    ChapaInitializeForAppointmentRequest,
    ChapaInitializeResponse,
    PaymentResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])
payment_service = PaymentService()


@router.post(
    "/appointments/{appointment_id}/chapa/initialize",
    response_model=ChapaInitializeResponse,
)
def initialize_chapa_payment_for_appointment(
    appointment_id: int,
    payload: ChapaInitializeForAppointmentRequest,
    db: Annotated[Session, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> ChapaInitializeResponse:
    payment = payment_service.initialize_chapa_for_appointment(
        db,
        appointment_id=appointment_id,
        patient_id=current_patient.id,
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        callback_url=payload.callback_url,
        return_url=payload.return_url,
    )
    return ChapaInitializeResponse(tx_ref=payment.tx_ref, checkout_url=payment.checkout_url or "")


@router.get("/chapa/verify/{tx_ref}", response_model=PaymentResponse)
def verify_chapa_payment(
    tx_ref: str,
    db: Annotated[Session, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> PaymentResponse:
    payment = payment_service.verify_chapa_payment(db, tx_ref=tx_ref, patient_id=current_patient.id)
    return PaymentResponse.model_validate(payment)


@router.get("/chapa/callback", response_model=PaymentResponse)
def chapa_callback(
    trx_ref: Annotated[str, Query(alias="trx_ref")],
    db: Annotated[Session, Depends(get_db)],
) -> PaymentResponse:
    # Callback is not authenticated; we still verify using the secret key server-side.
    payment = payment_service.verify_chapa_payment(db, tx_ref=trx_ref, patient_id=None)
    return PaymentResponse.model_validate(payment)

