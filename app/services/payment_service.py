from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.appointment import Appointment, ServiceCatalog
from app.models.payment import Payment, PaymentStatus
from app.services.chapa_service import ChapaService


class PaymentService:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.chapa = ChapaService(base_url=settings.chapa_base_url, secret_key=settings.chapa_secret_key)

    async def initialize_chapa_for_appointment(
        self,
        db: AsyncSession,
        *,
        appointment_id: int,
        patient_id: int,
        email: str,
        first_name: str,
        last_name: str,
        phone_number: str | None,
        callback_url: str | None,
        return_url: str | None,
    ) -> Payment:
        if not self.settings.chapa_secret_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chapa secret key is not configured",
            )

        appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.patient_id == patient_id))
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        service = await db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id))
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        tx_ref = f"heallink-appt-{appointment.id}-{uuid4().hex}"

        effective_callback_url = callback_url or self.settings.chapa_callback_url
        effective_return_url = return_url or self.settings.chapa_return_url

        payload: dict = {
            "amount": str(service.price),
            "currency": "ETB",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": tx_ref,
            "customization": {
                "title": "HealLink appointment payment",
                "description": f"Payment for appointment #{appointment.id}",
            },
            "meta": {"appointment_id": appointment.id, "patient_id": patient_id},
        }
        if phone_number:
            payload["phone_number"] = phone_number
        if effective_callback_url:
            payload["callback_url"] = effective_callback_url
        if effective_return_url:
            payload["return_url"] = effective_return_url

        init_result = self.chapa.initialize_transaction(payload)

        payment = Payment(
            patient_id=patient_id,
            appointment_id=appointment.id,
            provider="chapa",
            tx_ref=tx_ref,
            amount=float(service.price),
            currency="ETB",
            status=PaymentStatus.PENDING,
            checkout_url=init_result.checkout_url,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    async def verify_chapa_payment(self, db: AsyncSession, *, tx_ref: str, patient_id: int | None = None) -> Payment:
        stmt = select(Payment).where(Payment.tx_ref == tx_ref, Payment.provider == "chapa")
        if patient_id is not None:
            stmt = stmt.where(Payment.patient_id == patient_id)
        payment = await db.scalar(stmt)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        verify_result = self.chapa.verify_transaction(tx_ref)

        payment.chapa_reference = verify_result.reference
        status_value = (verify_result.status or "").lower()
        if status_value == "success":
            payment.status = PaymentStatus.SUCCESS
        elif status_value in {"failed", "cancelled"}:
            payment.status = PaymentStatus.FAILED
        else:
            payment.status = PaymentStatus.PENDING

        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

