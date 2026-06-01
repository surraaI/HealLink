from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.provider import Provider
from app.schemas.review import ProviderRatingSummary, ReviewResponse, SubmitReviewRequest
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])
review_service = ReviewService()


@router.post("", response_model=ReviewResponse)
async def submit_review(
    payload: SubmitReviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> ReviewResponse:
    from app.models.appointment import ServiceCatalog

    appointment = await db.scalar(
        select(Appointment).where(Appointment.id == payload.appointment_id)
    )
    if not appointment:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    service = await db.scalar(
        select(ServiceCatalog).where(ServiceCatalog.id == appointment.service_id)
    )
    if not service:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    review = await review_service.submit_review(
        db,
        patient_id=current_patient.id,
        appointment_id=payload.appointment_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return ReviewResponse.model_validate(review)


@router.get("/providers/{provider_id}", response_model=ProviderRatingSummary)
async def get_provider_reviews(
    provider_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query()] = 20,
    offset: Annotated[int, Query()] = 0,
) -> ProviderRatingSummary:
    from app.models.appointment import ServiceCatalog

    provider = await db.scalar(select(Provider).where(Provider.id == provider_id))
    if not provider:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    reviews = await review_service.get_provider_reviews(db, provider_id, limit, offset)
    return ProviderRatingSummary(
        provider_id=provider_id,
        average_rating=provider.average_rating,
        review_count=provider.review_count,
        reviews=[ReviewResponse.model_validate(review) for review in reviews],
    )


@router.get("/appointments/{appointment_id}", response_model=ReviewResponse)
async def get_review_for_appointment(
    appointment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> ReviewResponse:
    appointment = await db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if not appointment:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if appointment.patient_id != current_patient.id:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this appointment",
        )

    review = await review_service.get_review_by_appointment(db, appointment_id)
    if not review:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return ReviewResponse.model_validate(review)
