from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False, index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),)
