from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLAlchemyEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderType(str, Enum):
    DOCTOR = "DOCTOR"
    CLINIC = "CLINIC"
    DIAGNOSTIC_CENTER = "DIAGNOSTIC_CENTER"


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(SQLAlchemyEnum(ProviderType), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tin_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda ctx=None: datetime.utcnow(), nullable=False)

    # Verification fields
    verification_status: Mapped[str] = mapped_column(
        SQLAlchemyEnum("pending", "approved", "rejected", name="verificationstatus"),
        default="pending",
        server_default="pending",
    )
    license_document_url: Mapped[str | None] = mapped_column(String(500))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Rating fields
    average_rating: Mapped[float] = mapped_column(default=0.0, server_default="0")
    review_count: Mapped[int] = mapped_column(default=0, server_default="0")


class ServiceSlot(Base):
    __tablename__ = "service_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service_catalog.id"), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_booked: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda ctx=None: datetime.utcnow(), nullable=False)
