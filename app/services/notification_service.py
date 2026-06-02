import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
import smtplib
from socket import gaierror, timeout as socket_timeout
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.notification import Notification, NotificationChannel

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    def send_email(self, to_email: str, subject: str, body_plain: str) -> bool:
        return self._send_email_external(to_email, subject, body_plain)

    async def stage_patient_event(
        self,
        db: AsyncSession,
        *,
        patient_id: int | None,
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
            ok = self.send_email(patient_email, title, body)
            mail.email_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            mail.email_failed = not ok
            db.add(mail)
        elif patient_email:
            logger.warning(
                "Skipping email notification for patient %s because notifications_email_enabled is disabled",
                patient_email,
            )
        await db.flush()
        return in_app

    async def stage_officer_event(self, db: AsyncSession, *, title: str, body: str) -> Notification:
        """Create an officer-scoped notification (not tied to a patient). Does not commit."""
        in_app = Notification(
            patient_id=None,
            channel=NotificationChannel.OFFICER,
            title=title,
            body=body,
            appointment_id=None,
            read_at=None,
        )
        db.add(in_app)
        await db.flush()
        return in_app

    async def list_for_patient(
        self, db: AsyncSession, patient_id: int, include_read: bool, limit: int
    ) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.patient_id == patient_id)
            .where(Notification.channel == NotificationChannel.IN_APP)
        )
        if not include_read:
            statement = statement.where(Notification.read_at.is_(None))
        statement = statement.order_by(Notification.created_at.desc()).limit(limit)
        res = await db.scalars(statement)
        return list(res.all())

    async def mark_read(self, db: AsyncSession, notification_id: int, patient_id: int) -> Notification:
        from fastapi import HTTPException, status

        notif = await db.scalar(
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
        await db.commit()
        await db.refresh(notif)
        return notif

    def _send_email_external(self, to_email: str, subject: str, body_plain: str) -> bool:
        """Send email via Brevo SMTP with retry logic and alternative ports."""
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            logger.warning("Brevo SMTP settings are incomplete; skipping email to %s", to_email)
            return False
        
        if not settings.smtp_from_email:
            logger.error("SMTP_FROM_EMAIL is not configured; skipping email to %s", to_email)
            return False
        
        sender = settings.smtp_from_email
        ports_to_try = settings.smtp_alternative_ports
        max_retries = 2
        
        for port in ports_to_try:
            for attempt in range(max_retries):
                logger.info(
                    "Attempting to send email to %s using sender %s via %s:%s (port %d, attempt %d/%d)",
                    to_email,
                    sender,
                    settings.smtp_host,
                    port,
                    port,
                    attempt + 1,
                    max_retries,
                )
                
                try:
                    message = EmailMessage()
                    message["From"] = f"HealLink <{sender}>"
                    message["To"] = to_email
                    message["Subject"] = subject
                    message.set_content(body_plain)
                    message.add_alternative(
                        (
                            "<div style='font-family: Arial, sans-serif; max-width: 600px; line-height: 1.6;'>"
                            f"{escape(body_plain).replace(chr(10), '<br>')}"
                            "</div>"
                        ),
                        subtype="html",
                    )

                    with smtplib.SMTP(settings.smtp_host, port, timeout=settings.smtp_timeout_seconds) as server:
                        server.ehlo()
                        if port != 465:  # 465 is typically SSL, not STARTTLS
                            server.starttls()
                            server.ehlo()
                        server.login(settings.smtp_user, settings.smtp_password)
                        server.send_message(message)

                    logger.info("Email sent successfully via Brevo SMTP to %s from %s on port %d", to_email, sender, port)
                    return True
                except socket_timeout:
                    logger.warning(
                        "Brevo SMTP connection timed out for %s via %s:%d after %ss (attempt %d/%d)",
                        to_email,
                        settings.smtp_host,
                        port,
                        settings.smtp_timeout_seconds,
                        attempt + 1,
                        max_retries,
                    )
                    if attempt < max_retries - 1:
                        delay = 1.0 * (2 ** attempt)
                        logger.info("Retrying port %d in %.1f seconds...", port, delay)
                        time.sleep(delay)
                    else:
                        logger.warning("All attempts failed for port %d, trying next port", port)
                        break
                except gaierror:
                    logger.exception(
                        "Brevo SMTP host resolution failed for %s via %s:%d",
                        to_email,
                        settings.smtp_host,
                        port,
                    )
                    return False
                except Exception as e:
                    logger.warning(
                        "Brevo SMTP email failed to %s from %s via %s:%d (attempt %d/%d): %s",
                        to_email,
                        sender,
                        settings.smtp_host,
                        port,
                        attempt + 1,
                        max_retries,
                        str(e),
                    )
                    if attempt < max_retries - 1:
                        delay = 1.0 * (2 ** attempt)
                        logger.info("Retrying port %d in %.1f seconds...", port, delay)
                        time.sleep(delay)
                    else:
                        logger.warning("All attempts failed for port %d, trying next port", port)
                        break
        
        logger.error("All SMTP ports failed for %s", to_email)
        return False
