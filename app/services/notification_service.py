import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification, NotificationChannel

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    def stage_patient_event(
        self,
        db: Session,
        *,
        patient_id: int,
        patient_email: str | None,
        title: str,
        body: str,
        appointment_id: int | None = None,
    ) -> Notification:
        """Insert in-app notification and optional email audit row; does not commit."""
        in_app = Notification(
            patient_id=patient_id,
            channel=NotificationChannel.IN_APP,
            title=title,
            body=body,
            appointment_id=appointment_id,
            read_at=None,
        )
        db.add(in_app)

        if settings.notifications_email_enabled and patient_email:
            mail = Notification(
                patient_id=patient_id,
                channel=NotificationChannel.EMAIL,
                title=title,
                body=body,
                appointment_id=appointment_id,
                read_at=None,
                email_attempted_at=None,
                email_failed=False,
            )
            ok = self._send_email_external(patient_email, title, body)
            mail.email_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            mail.email_failed = not ok
            db.add(mail)

        db.flush()
        return in_app

    def list_for_patient(
        self, db: Session, patient_id: int, include_read: bool, limit: int
    ) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.patient_id == patient_id)
            .where(Notification.channel == NotificationChannel.IN_APP)
        )
        if not include_read:
            statement = statement.where(Notification.read_at.is_(None))
        statement = statement.order_by(Notification.created_at.desc()).limit(limit)
        return list(db.scalars(statement).all())

    def mark_read(self, db: Session, notification_id: int, patient_id: int) -> Notification:
        from fastapi import HTTPException, status

        notif = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.patient_id == patient_id,
                Notification.channel == NotificationChannel.IN_APP,
            )
        )
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        notif.read_at = now
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    def _send_email_external(self, to_email: str, subject: str, body_plain: str) -> bool:
        if not settings.smtp_host or not settings.smtp_from_email:
            logger.warning("Email notification skipped: SMTP not fully configured.")
            return False
        msg = MIMEText(body_plain, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                if smtp.has_extn("STARTTLS"):
                    smtp.starttls()
                    smtp.ehlo()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        except Exception as exc:  # noqa: BLE001
            logger.exception("SMTP send failed: %s", exc)
            return False
        return True
