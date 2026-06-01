from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.provider import Provider
from app.models.review import Review


class ReviewService:
    async def submit_review(
        self,
        db: AsyncSession,
        patient_id: int,
        appointment_id: int,
        rating: int,
        comment: str | None,
    ) -> Review:
        appointment = await db.scalar(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )
        if appointment.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to review this appointment",
            )
        if appointment.status != AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only review completed appointments",
            )

        existing_review = await db.scalar(
            select(Review).where(Review.appointment_id == appointment_id)
        )
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this appointment",
            )

        review = Review(
            patient_id=patient_id,
            provider_id=appointment.service_id,
            appointment_id=appointment_id,
            rating=rating,
            comment=comment,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        await self._update_provider_rating(db, appointment.service_id)
        return review

    async def _update_provider_rating(self, db: AsyncSession, provider_id: int) -> None:
        from app.models.appointment import ServiceCatalog

        service = await db.scalar(
            select(ServiceCatalog).where(ServiceCatalog.id == provider_id)
        )
        if not service or not service.provider_id:
            return

        actual_provider_id = service.provider_id

        stmt = select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.provider_id == provider_id
        )
        result = await db.execute(stmt)
        avg_rating, count = result.one()

        provider = await db.scalar(select(Provider).where(Provider.id == actual_provider_id))
        if provider:
            provider.average_rating = float(avg_rating) if avg_rating else 0.0
            provider.review_count = int(count) if count else 0
            db.add(provider)
            await db.commit()

    async def get_provider_reviews(
        self, db: AsyncSession, provider_id: int, limit: int = 20, offset: int = 0
    ) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.provider_id == provider_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await db.scalars(stmt)
        return list(res.all())

    async def get_review_by_appointment(self, db: AsyncSession, appointment_id: int) -> Review | None:
        return await db.scalar(select(Review).where(Review.appointment_id == appointment_id))
