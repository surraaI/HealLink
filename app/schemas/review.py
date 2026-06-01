from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubmitReviewRequest(BaseModel):
    appointment_id: int
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    provider_id: int
    appointment_id: int
    rating: int
    comment: str | None
    created_at: datetime


class ProviderRatingSummary(BaseModel):
    provider_id: int
    average_rating: float
    review_count: int
    reviews: list[ReviewResponse]
