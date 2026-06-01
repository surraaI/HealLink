import base64
import io
import random
import string

import qrcode
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.qr_checkin import QRCheckin, QRCheckinStatus
from app.schemas.qr_checkin import VerifyCheckinRequest


class QRCheckinService:
    def _generate_card_number(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    def _generate_qr_image_b64(self, card_number: str) -> str:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(card_number)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode("utf-8")

    async def _is_code_active(self, db: AsyncSession, card_number: str) -> bool:
        stmt = select(QRCheckin).where(
            QRCheckin.card_number == card_number,
            QRCheckin.status == QRCheckinStatus.ACTIVE,
        )
        result = await db.scalar(stmt)
        return result is not None

    async def generate_checkin(self, db: AsyncSession, appointment_id: int) -> QRCheckin:
        from datetime import datetime, timedelta, timezone

        existing = await db.scalar(
            select(QRCheckin).where(QRCheckin.appointment_id == appointment_id)
        )

        if existing:
            if existing.status == QRCheckinStatus.ACTIVE:
                return existing

            for attempt in range(10):
                card_number = self._generate_card_number()
                if not await self._is_code_active(db, card_number):
                    existing.card_number = card_number
                    existing.qr_image_b64 = self._generate_qr_image_b64(card_number)
                    existing.status = QRCheckinStatus.ACTIVE
                    existing.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
                    existing.used_at = None
                    existing.used_by_provider_id = None
                    db.add(existing)
                    await db.commit()
                    await db.refresh(existing)
                    return existing

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No codes available, try again shortly",
            )

        for attempt in range(10):
            card_number = self._generate_card_number()
            if not await self._is_code_active(db, card_number):
                from datetime import datetime, timedelta, timezone

                qr_checkin = QRCheckin(
                    appointment_id=appointment_id,
                    card_number=card_number,
                    qr_image_b64=self._generate_qr_image_b64(card_number),
                    status=QRCheckinStatus.ACTIVE,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                )
                db.add(qr_checkin)
                await db.commit()
                await db.refresh(qr_checkin)
                return qr_checkin

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No codes available, try again shortly",
        )

    async def get_checkin_by_appointment(self, db: AsyncSession, appointment_id: int) -> QRCheckin | None:
        return await db.scalar(
            select(QRCheckin).where(QRCheckin.appointment_id == appointment_id)
        )

    async def verify_and_checkin(
        self, db: AsyncSession, card_number: str, provider_id: int
    ) -> QRCheckin:
        from datetime import datetime, timezone

        stmt = select(QRCheckin).where(QRCheckin.card_number == card_number)
        qr_checkin = await db.scalar(stmt)

        if not qr_checkin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check-in code not found",
            )

        if qr_checkin.status == QRCheckinStatus.USED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Check-in code already used",
            )

        if qr_checkin.status == QRCheckinStatus.EXPIRED or qr_checkin.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Check-in code has expired",
            )

        appointment = await db.scalar(
            select(Appointment).where(Appointment.id == qr_checkin.appointment_id)
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        qr_checkin.status = QRCheckinStatus.USED
        qr_checkin.used_at = datetime.now(timezone.utc)
        qr_checkin.used_by_provider_id = provider_id

        appointment.status = AppointmentStatus.CHECKED_IN
        appointment.check_in_time = datetime.now(timezone.utc)

        db.add(qr_checkin)
        db.add(appointment)
        await db.commit()
        await db.refresh(qr_checkin)
        return qr_checkin

    async def expire_old_checkins(self, db: AsyncSession) -> int:
        from datetime import datetime, timezone

        from sqlalchemy import update

        stmt = (
            update(QRCheckin)
            .where(
                QRCheckin.status == QRCheckinStatus.ACTIVE,
                QRCheckin.expires_at < datetime.now(timezone.utc),
            )
            .values(status=QRCheckinStatus.EXPIRED)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount
