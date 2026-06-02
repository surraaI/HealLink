from datetime import datetime, timedelta

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment import ServiceCatalog


class AnalyticsService:
    async def get_overall_stats(self, db: AsyncSession, provider_id: int, days: int) -> dict:
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(
            func.count(Appointment.id).label("total_appointments"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.COMPLETED)
            .label("completed"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.CANCELLED)
            .label("cancelled"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.BOOKED)
            .filter(Appointment.appointment_at < datetime.utcnow())
            .label("no_shows"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.CHECKED_IN)
            .label("checked_in"),
            func.count(Appointment.id)
            .filter(Appointment.status == AppointmentStatus.BOOKED)
            .filter(Appointment.appointment_at >= datetime.utcnow())
            .label("pending"),
        ).where(
            and_(
                Appointment.appointment_at >= start_date,
                Appointment.service_id == ServiceCatalog.id,
                ServiceCatalog.provider_id == provider_id,
            )
        )

        result = await db.execute(stmt)
        row = result.one()

        total_appointments = row.total_appointments or 0
        no_shows = row.no_shows or 0
        no_show_rate = (no_shows / total_appointments * 100) if total_appointments > 0 else 0.0

        from app.schemas.analytics import OverallStatsResponse

        return OverallStatsResponse(
            total_appointments=total_appointments,
            completed=row.completed or 0,
            cancelled=row.cancelled or 0,
            no_shows=no_shows,
            no_show_rate=round(no_show_rate, 2),
            checked_in=row.checked_in or 0,
            pending=row.pending or 0,
            days_scoped=days,
        ).model_dump()

    async def get_peak_hours(self, db: AsyncSession, provider_id: int, days: int) -> list[dict]:
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                extract("hour", Appointment.appointment_at).label("hour"),
                func.count(Appointment.id).label("appointment_count"),
            )
            .where(
                and_(
                    Appointment.appointment_at >= start_date,
                    Appointment.service_id == ServiceCatalog.id,
                    ServiceCatalog.provider_id == provider_id,
                )
            )
            .group_by(extract("hour", Appointment.appointment_at))
            .order_by(func.count(Appointment.id).desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        from app.schemas.analytics import PeakHoursResponse

        return [PeakHoursResponse(hour=int(row.hour), appointment_count=row.appointment_count).model_dump() for row in rows]

    async def get_daily_trend(self, db: AsyncSession, provider_id: int, days: int) -> list[dict]:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()

        stmt = (
            select(
                func.date(Appointment.appointment_at).label("date"),
                func.count(Appointment.id).label("appointment_count"),
            )
            .where(
                and_(
                    Appointment.appointment_at >= start_date,
                    Appointment.appointment_at <= end_date,
                    Appointment.service_id == ServiceCatalog.id,
                    ServiceCatalog.provider_id == provider_id,
                )
            )
            .group_by(func.date(Appointment.appointment_at))
            .order_by(func.date(Appointment.appointment_at))
        )

        result = await db.execute(stmt)
        rows = result.all()

        date_counts = {row.date: row.appointment_count for row in rows}

        from app.schemas.analytics import DailyTrendResponse

        trend_data = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            trend_data.append(
                DailyTrendResponse(
                    date=datetime.combine(current_date, datetime.min.time()),
                    appointment_count=date_counts.get(current_date, 0),
                ).model_dump()
            )
            current_date += timedelta(days=1)

        return trend_data

    async def get_service_breakdown(self, db: AsyncSession, provider_id: int, days: int) -> list[dict]:
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                ServiceCatalog.name.label("service_name"),
                func.count(Appointment.id).label("appointment_count"),
            )
            .join(Appointment, Appointment.service_id == ServiceCatalog.id)
            .where(
                and_(
                    Appointment.appointment_at >= start_date,
                    ServiceCatalog.provider_id == provider_id,
                )
            )
            .group_by(ServiceCatalog.name)
            .order_by(func.count(Appointment.id).desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        from app.schemas.analytics import ServiceBreakdownResponse

        return [
            ServiceBreakdownResponse(service_name=row.service_name, appointment_count=row.appointment_count).model_dump()
            for row in rows
        ]
