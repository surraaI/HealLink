from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    title: str
    body: str
    appointment_id: int | None
    read_at: datetime | None
    created_at: datetime
