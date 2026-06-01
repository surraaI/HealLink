from datetime import datetime, time
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class ProviderSchedule(Base):
    """Defines recurring availability patterns for providers."""
    __tablename__ = "provider_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False, index=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("service_catalog.id"), nullable=True, index=True)
    
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SqlEnum(ScheduleType), default=ScheduleType.WEEKLY, nullable=False
    )
    
    # For weekly schedules: 0=Monday, 1=Tuesday, ..., 6=Sunday
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Time range for availability
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    
    # Slot duration in minutes (e.g., 30, 60)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Validity period
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda ctx=None: datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda ctx=None: datetime.utcnow(), onupdate=lambda ctx=None: datetime.utcnow(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "service_id", "day_of_week", "start_time", name="unique_provider_schedule_slot"),
    )
