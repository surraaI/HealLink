from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_patient
from app.db.session import get_db
from app.models.patient import Patient
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])
notification_service = NotificationService()


@router.get("/mine", response_model=list[NotificationResponse])
def list_my_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
    include_read: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(le=200, ge=1)] = 50,
) -> list[NotificationResponse]:
    items = notification_service.list_for_patient(
        db, patient_id=current_patient.id, include_read=include_read, limit=limit
    )
    return [NotificationResponse.model_validate(n) for n in items]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_patient: Annotated[Patient, Depends(get_current_patient)],
) -> NotificationResponse:
    notif = notification_service.mark_read(db, notification_id, current_patient.id)
    return NotificationResponse.model_validate(notif)
