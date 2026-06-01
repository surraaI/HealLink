from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QRCheckinStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"


class QRCheckin(Base):
    __tablename__ = "qr_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=False, index=True
    )
    card_number: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    qr_image_b64: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[QRCheckinStatus] = mapped_column(
        SqlEnum(QRCheckinStatus), default=QRCheckinStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.id"), nullable=True
    )
