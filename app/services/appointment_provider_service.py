from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, ServiceCatalog
from app.models.patient import Patient
from app.models.provider import ServiceSlot
from app.services.notification_service import NotificationService
from app.services.qr_checkin_service import QRCheckinService


class AppointmentProviderService:
    def __init__(self) -> None:
        self.notification_service = NotificationService()
        self.qr_service = QRCheckinService()

    async def _get_managed_appointment(
        self, db: AsyncSession, provider_id: int, appointment_id: int
    ) -> tuple[Appointment, ServiceCatalog]:
        appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id))
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        service = await db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id))
        if not service or service.provider_id != provider_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Provider cannot manage this appointment",
            )
        return appointment, service

    async def mark_completed(self, db: AsyncSession, provider_id: int, appointment_id: int) -> Appointment:
        appointment, _ = await self._get_managed_appointment(db, provider_id, appointment_id)
        if appointment.status != AppointmentStatus.BOOKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked appointments can be marked completed",
            )
        appointment.status = AppointmentStatus.COMPLETED
        db.add(appointment)
        await db.flush()
        return appointment

    async def mark_needs_recheck(self, db: AsyncSession, provider_id: int, appointment_id: int, reason: str | None):
        appointment, _ = await self._get_managed_appointment(db, provider_id, appointment_id)
        if appointment.status not in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked or completed visits can be marked for recheck",
            )
        if appointment.status == AppointmentStatus.BOOKED and appointment.slot_id:
            slot = await db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
            if slot:
                slot.is_booked = False
                db.add(slot)
            appointment.slot_id = None

        appointment.status = AppointmentStatus.NEEDS_RECHECK
        appointment.provider_recheck_reason = reason.strip() if reason else None
        db.add(appointment)
        await db.flush()
        return appointment

    async def book_follow_up(
        self, db: AsyncSession, provider_id: int, appointment_id: int, slot_id: int
    ) -> tuple[Appointment, Appointment]:
        original, _ = await self._get_managed_appointment(db, provider_id, appointment_id)
        if original.status != AppointmentStatus.NEEDS_RECHECK:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule a follow-up only after the visit is marked as needing recheck.",
            )

        slot = await db.scalar(
            select(ServiceSlot).where(
                ServiceSlot.id == slot_id,
                ServiceSlot.service_id == original.service_id,
            )
        )
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Slot not found for this service",
            )
        if slot.is_booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot is already booked",
            )
        start = slot.starts_at
        if start <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot time must be in the future",
            )

        new_appointment = Appointment(
            patient_id=original.patient_id,
            service_id=original.service_id,
            slot_id=slot.id,
            appointment_at=start,
            status=AppointmentStatus.BOOKED,
            follow_up_of_id=original.id,
            note="Follow-up / recheck visit",
        )

        slot.is_booked = True

        db.add(slot)
        db.add(new_appointment)
        await db.flush()

        original.continuation_appointment_id = new_appointment.id
        original.status = AppointmentStatus.FOLLOW_UP_BOOKED
        db.add(original)

        await db.flush()
        return new_appointment, original

    async def reschedule_appointment(
        self,
        db: AsyncSession,
        provider_id: int,
        appointment_id: int,
        new_slot_id: int,
    ) -> Appointment:
        """Reschedule an appointment to a new slot and reactivate QR code."""
        appointment, service = await self._get_managed_appointment(db, provider_id, appointment_id)
        
        # Validate appointment status
        if appointment.status not in (AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked, checked-in, or completed appointments can be rescheduled",
            )
        
        # Get new slot
        new_slot = await db.scalar(
            select(ServiceSlot).where(
                ServiceSlot.id == new_slot_id,
                ServiceSlot.service_id == appointment.service_id,
            )
        )
        if not new_slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Slot not found for this service",
            )
        if new_slot.is_booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot is already booked",
            )
        if new_slot.starts_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot time must be in the future",
            )
        
        # Free up old slot if exists
        if appointment.slot_id:
            old_slot = await db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
            if old_slot:
                old_slot.is_booked = False
                db.add(old_slot)
        
        # Update appointment
        appointment.slot_id = new_slot.id
        appointment.appointment_at = new_slot.starts_at
        appointment.status = AppointmentStatus.BOOKED
        new_slot.is_booked = True
        db.add(new_slot)
        db.add(appointment)
        await db.flush()
        
        # Reactivate QR code if exists
        qr_checkin = await self.qr_service.get_checkin_by_appointment(db, appointment.id)
        if qr_checkin:
            qr_checkin.status = "active"
            qr_checkin.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            qr_checkin.used_at = None
            qr_checkin.used_by_provider_id = None
            db.add(qr_checkin)
            await db.flush()
        
        # Send notification to patient
        patient = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
        if patient:
            await self.notification_service.stage_patient_event(
                db,
                patient_id=patient.id,
                patient_email=patient.email,
                title="Appointment rescheduled",
                body=f"Your appointment has been rescheduled to {appointment.appointment_at}.",
                appointment_id=appointment.id,
            )
        
        await db.commit()
        await db.refresh(appointment)
        return appointment
