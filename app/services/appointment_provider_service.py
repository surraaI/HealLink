from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus, ServiceCatalog
from app.models.provider import ServiceSlot


class AppointmentProviderService:
    def _get_managed_appointment(
        self, db: Session, provider_id: int, appointment_id: int
    ) -> tuple[Appointment, ServiceCatalog]:
        appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        service = db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id))
        if not service or service.provider_id != provider_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Provider cannot manage this appointment",
            )
        return appointment, service

    def mark_completed(self, db: Session, provider_id: int, appointment_id: int) -> Appointment:
        appointment, _ = self._get_managed_appointment(db, provider_id, appointment_id)
        if appointment.status != AppointmentStatus.BOOKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked appointments can be marked completed",
            )
        appointment.status = AppointmentStatus.COMPLETED
        db.add(appointment)
        db.flush()
        return appointment

    def mark_needs_recheck(self, db: Session, provider_id: int, appointment_id: int, reason: str | None):
        appointment, _ = self._get_managed_appointment(db, provider_id, appointment_id)
        if appointment.status not in (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only booked or completed visits can be marked for recheck",
            )
        if appointment.status == AppointmentStatus.BOOKED and appointment.slot_id:
            slot = db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
            if slot:
                slot.is_booked = False
                db.add(slot)
            appointment.slot_id = None

        appointment.status = AppointmentStatus.NEEDS_RECHECK
        appointment.provider_recheck_reason = reason.strip() if reason else None
        db.add(appointment)
        db.flush()
        return appointment

    def book_follow_up(
        self, db: Session, provider_id: int, appointment_id: int, slot_id: int
    ) -> tuple[Appointment, Appointment]:
        original, _ = self._get_managed_appointment(db, provider_id, appointment_id)
        if original.status != AppointmentStatus.NEEDS_RECHECK:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule a follow-up only after the visit is marked as needing recheck.",
            )

        slot = db.scalar(
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
        db.flush()

        original.continuation_appointment_id = new_appointment.id
        original.status = AppointmentStatus.FOLLOW_UP_BOOKED
        db.add(original)

        db.flush()
        return new_appointment, original
