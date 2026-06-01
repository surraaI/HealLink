from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.diagnostic_result import DiagnosticResult, DiagnosticResultStatus
from app.models.patient import Patient
from app.models.provider import Provider
from app.services.notification_service import NotificationService


class DiagnosticResultService:
    def __init__(self) -> None:
        self.notification_service = NotificationService()

    async def get_or_create_result(self, db: AsyncSession, appointment_id: int) -> DiagnosticResult:
        existing = await db.scalar(
            select(DiagnosticResult).where(DiagnosticResult.appointment_id == appointment_id)
        )
        if existing:
            return existing

        result = DiagnosticResult(
            appointment_id=appointment_id,
            status=DiagnosticResultStatus.PENDING,
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        return result

    async def update_status(
        self, db: AsyncSession, appointment_id: int, new_status: str, provider_id: int
    ) -> DiagnosticResult:
        result = await db.scalar(
            select(DiagnosticResult).where(DiagnosticResult.appointment_id == appointment_id)
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnostic result not found",
            )

        valid_transitions = {
            DiagnosticResultStatus.PENDING: [DiagnosticResultStatus.READY],
            DiagnosticResultStatus.READY: [DiagnosticResultStatus.COLLECTED],
            DiagnosticResultStatus.COLLECTED: [],
        }

        current_status = result.status
        allowed_next = valid_transitions.get(current_status, [])

        if new_status not in [s.value for s in allowed_next]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot move from '{current_status.value}' to '{new_status}'",
            )

        result.status = DiagnosticResultStatus(new_status)
        result.updated_by_provider_id = provider_id
        result.updated_at = datetime.now(timezone.utc)

        db.add(result)
        await db.commit()
        await db.refresh(result)

        # Send notification after successful status change
        appointment = await db.scalar(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        if appointment:
            patient = await db.scalar(select(Patient).where(Patient.id == appointment.patient_id))
            if patient:
                if current_status == DiagnosticResultStatus.PENDING and new_status == DiagnosticResultStatus.READY.value:
                    await self.notification_service.stage_patient_event(
                        db,
                        patient_id=patient.id,
                        patient_email=patient.email,
                        title="Your results are ready",
                        body="Your diagnostic results are ready for collection at the center.",
                        appointment_id=appointment_id,
                    )
                    await db.commit()
                elif current_status == DiagnosticResultStatus.READY and new_status == DiagnosticResultStatus.COLLECTED.value:
                    await self.notification_service.stage_patient_event(
                        db,
                        patient_id=patient.id,
                        patient_email=patient.email,
                        title="Results collected",
                        body="Your diagnostic results have been marked as collected.",
                        appointment_id=appointment_id,
                    )
                    await db.commit()

        return result

    async def get_result_by_appointment(self, db: AsyncSession, appointment_id: int) -> DiagnosticResult | None:
        return await db.scalar(
            select(DiagnosticResult).where(DiagnosticResult.appointment_id == appointment_id)
        )

    async def get_results_for_provider(self, db: AsyncSession, provider_id: int) -> list[DiagnosticResult]:
        from app.models.appointment import ServiceCatalog

        stmt = (
            select(DiagnosticResult)
            .join(Appointment, DiagnosticResult.appointment_id == Appointment.id)
            .join(ServiceCatalog, Appointment.service_id == ServiceCatalog.id)
            .where(ServiceCatalog.provider_id == provider_id)
            .order_by(DiagnosticResult.updated_at.desc())
        )
        res = await db.scalars(stmt)
        return list(res.all())
