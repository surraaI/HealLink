from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiagnosticResultStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    COLLECTED = "collected"


class DiagnosticResult(Base):
    __tablename__ = "diagnostic_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=False, index=True
    )
    status: Mapped[DiagnosticResultStatus] = mapped_column(
        SqlEnum(DiagnosticResultStatus), default=DiagnosticResultStatus.PENDING, nullable=False
    )
    updated_by_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
