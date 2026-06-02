from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.provider import Provider, ProviderType


class PlatformStatsService:
    async def get_platform_stats(self, db: AsyncSession) -> dict:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Total patients
        total_patients_stmt = select(func.count(Patient.id))
        total_patients = await db.scalar(total_patients_stmt)

        # Total providers
        total_providers_stmt = select(func.count(Provider.id))
        total_providers = await db.scalar(total_providers_stmt)

        # Provider verification stats
        verification_stats = await self._get_provider_verification_stats(db)

        # Provider type stats
        type_stats = await self._get_provider_type_stats(db)

        # Appointment status stats
        appointment_stats = await self._get_appointment_status_stats(db)

        # Revenue stats
        revenue_stats = await self._get_revenue_stats(db, thirty_days_ago)

        # New users stats
        new_users_stats = await self._get_new_users_stats(db, thirty_days_ago)

        from app.schemas.platform_stats import (
            AppointmentStatusStats,
            NewUsersStats,
            PlatformStatsResponse,
            ProviderTypeStats,
            ProviderVerificationStats,
            RevenueStats,
        )

        return PlatformStatsResponse(
            total_patients=total_patients or 0,
            total_providers=total_providers or 0,
            provider_verification_stats=ProviderVerificationStats(**verification_stats),
            provider_type_stats=ProviderTypeStats(**type_stats),
            appointment_status_stats=AppointmentStatusStats(**appointment_stats),
            revenue_stats=RevenueStats(**revenue_stats),
            new_users_stats=NewUsersStats(**new_users_stats),
        ).model_dump()

    async def _get_provider_verification_stats(self, db: AsyncSession) -> dict:
        stmt = select(
            func.count(Provider.id).filter(Provider.verification_status == "pending").label("pending"),
            func.count(Provider.id).filter(Provider.verification_status == "approved").label("approved"),
            func.count(Provider.id).filter(Provider.verification_status == "rejected").label("rejected"),
        )
        result = await db.execute(stmt)
        row = result.one()
        return {
            "pending": row.pending or 0,
            "approved": row.approved or 0,
            "rejected": row.rejected or 0,
            "total": (row.pending or 0) + (row.approved or 0) + (row.rejected or 0),
        }

    async def _get_provider_type_stats(self, db: AsyncSession) -> dict:
        stmt = select(
            func.count(Provider.id).filter(Provider.provider_type == ProviderType.DOCTOR).label("doctor"),
            func.count(Provider.id).filter(Provider.provider_type == ProviderType.CLINIC).label("clinic"),
            func.count(Provider.id)
            .filter(Provider.provider_type == ProviderType.DIAGNOSTIC_CENTER)
            .label("diagnostic_center"),
        )
        result = await db.execute(stmt)
        row = result.one()
        return {
            "doctor": row.doctor or 0,
            "clinic": row.clinic or 0,
            "diagnostic_center": row.diagnostic_center or 0,
            "total": (row.doctor or 0) + (row.clinic or 0) + (row.diagnostic_center or 0),
        }

    async def _get_appointment_status_stats(self, db: AsyncSession) -> dict:
        stmt = select(
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.BOOKED)
            .label("booked"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.COMPLETED)
            .label("completed"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.CANCELLED)
            .label("cancelled"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.NEEDS_RECHECK)
            .label("needs_recheck"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.FOLLOW_UP_BOOKED)
            .label("follow_up_booked"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.CHECKED_IN)
            .label("checked_in"),
        )
        result = await db.execute(stmt)
        row = result.one()
        return {
            "booked": row.booked or 0,
            "completed": row.completed or 0,
            "cancelled": row.cancelled or 0,
            "needs_recheck": row.needs_recheck or 0,
            "follow_up_booked": row.follow_up_booked or 0,
            "checked_in": row.checked_in or 0,
            "total": (row.booked or 0)
            + (row.completed or 0)
            + (row.cancelled or 0)
            + (row.needs_recheck or 0)
            + (row.follow_up_booked or 0)
            + (row.checked_in or 0),
        }

    async def _get_revenue_stats(self, db: AsyncSession, thirty_days_ago: datetime) -> dict:
        total_revenue_stmt = select(func.sum(Payment.amount))
        total_revenue = await db.scalar(total_revenue_stmt)

        last_30_days_stmt = select(func.sum(Payment.amount)).where(Payment.created_at >= thirty_days_ago)
        last_30_days_revenue = await db.scalar(last_30_days_stmt)

        return {
            "total_revenue": float(total_revenue or 0),
            "last_30_days_revenue": float(last_30_days_revenue or 0),
        }

    async def _get_new_users_stats(self, db: AsyncSession, thirty_days_ago: datetime) -> dict:
        new_patients_stmt = select(func.count(Patient.id)).where(Patient.created_at >= thirty_days_ago)
        new_patients = await db.scalar(new_patients_stmt)

        new_providers_stmt = select(func.count(Provider.id)).where(Provider.created_at >= thirty_days_ago)
        new_providers = await db.scalar(new_providers_stmt)

        return {
            "new_patients_last_30_days": new_patients or 0,
            "new_providers_last_30_days": new_providers or 0,
        }
