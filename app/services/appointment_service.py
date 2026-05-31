from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, ServiceCatalog
from app.models.patient import Patient
from app.models.provider import ServiceSlot
from app.schemas.appointment import AppointmentCreate
from app.services.notification_service import NotificationService


class AppointmentService:
    def __init__(self) -> None:
        self.notification_service = NotificationService()

    async def list_services(self, db: AsyncSession, service_type: str | None, location: str | None) -> list[ServiceCatalog]:
        statement: Select[tuple[ServiceCatalog]] = select(ServiceCatalog).where(ServiceCatalog.is_active.is_(True))
        if service_type:
            statement = statement.where(ServiceCatalog.service_type == service_type)
        if location:
            statement = statement.where(ServiceCatalog.location.ilike(f"%{location}%"))
        statement = statement.order_by(ServiceCatalog.created_at.desc())
        res = await db.scalars(statement)
        return list(res.all())

    async def create_appointment(
        self,
        db: AsyncSession,
        payload: AppointmentCreate,
        patient: Patient,
    ) -> Appointment:
        service = await db.scalar(
            select(ServiceCatalog).where(
                ServiceCatalog.id == payload.service_id, ServiceCatalog.is_active.is_(True)
            )
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found",
            )
        slot = await db.scalar(
            select(ServiceSlot).where(
                ServiceSlot.id == payload.slot_id,
                ServiceSlot.service_id == payload.service_id,
            )
        )
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Slot not found for selected service",
            )
        if slot.is_booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot is already booked",
            )
        appointment_time = slot.starts_at
        if appointment_time <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot time must be in the future",
            )

        appointment = Appointment(
            patient_id=patient.id,
            service_id=payload.service_id,
            slot_id=slot.id,
            appointment_at=appointment_time,
            note=payload.note,
        )
        slot.is_booked = True
        db.add(slot)
        db.add(appointment)
        await db.flush()
        await self.notification_service.stage_patient_event(
            db,
            patient_id=patient.id,
            patient_email=patient.email,
            title="Appointment confirmed",
            body=f"Your visit is scheduled for {appointment.appointment_at}.",
            appointment_id=appointment.id,
        )
        await db.commit()
        await db.refresh(appointment)
        return appointment

    async def list_patient_appointments(self, db: AsyncSession, patient_id: int) -> list[Appointment]:
        statement = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_at.desc())
        )
        res = await db.scalars(statement)
        return list(res.all())

    async def cancel_appointment(self, db: AsyncSession, appointment_id: int, patient_id: int) -> Appointment:
        appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id))
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )
        if appointment.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to cancel this appointment",
            )
        if appointment.status != AppointmentStatus.BOOKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked appointments can be cancelled",
            )
        appointment.status = AppointmentStatus.CANCELLED
        if appointment.slot_id:
            slot = await db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
            if slot:
                slot.is_booked = False
                db.add(slot)
        db.add(appointment)
        await db.flush()
        patient_row = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
        await self.notification_service.stage_patient_event(
            db,
            patient_id=appointment.patient_id,
            patient_email=patient_row.email if patient_row else None,
            title="Appointment cancelled",
            body="Your appointment has been cancelled.",
            appointment_id=appointment.id,
        )
        await db.commit()
        await db.refresh(appointment)
        return appointment
