from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthEvent(Base):
    __tablename__ = "health_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String(100), nullable=False, default="api")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="healthy")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
