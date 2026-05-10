from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus, ServiceCatalog
from app.models.patient import Patient
from app.models.provider import ServiceSlot
from app.schemas.appointment import AppointmentCreate


class AppointmentService:
    def list_services(self, db: Session, service_type: str | None, location: str | None) -> list[ServiceCatalog]:
        statement: Select[tuple[ServiceCatalog]] = select(ServiceCatalog).where(ServiceCatalog.is_active.is_(True))
        if service_type:
            statement = statement.where(ServiceCatalog.service_type == service_type)
        if location:
            statement = statement.where(ServiceCatalog.location.ilike(f"%{location}%"))
        statement = statement.order_by(ServiceCatalog.created_at.desc())
        return list(db.scalars(statement).all())

    def create_appointment(
        self,
        db: Session,
        payload: AppointmentCreate,
        patient: Patient,
    ) -> Appointment:
        service = db.scalar(
            select(ServiceCatalog).where(
                ServiceCatalog.id == payload.service_id, ServiceCatalog.is_active.is_(True)
            )
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found",
            )
        slot = db.scalar(
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
        if appointment_time <= datetime.utcnow():
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
        db.commit()
        db.refresh(appointment)
        return appointment

    def list_patient_appointments(self, db: Session, patient_id: int) -> list[Appointment]:
        statement = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_at.desc())
        )
        return list(db.scalars(statement).all())

    def cancel_appointment(self, db: Session, appointment_id: int, patient_id: int) -> Appointment:
        appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
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
            slot = db.scalar(select(ServiceSlot).where(ServiceSlot.id == appointment.slot_id))
            if slot:
                slot.is_booked = False
                db.add(slot)
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return appointment
