from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, hash_token
from app.models.account_action_token import AccountActionPurpose, AccountActionToken
from app.models.patient import Patient
from app.models.refresh_token import RefreshToken
from app.services.notification_service import NotificationService

settings = get_settings()


class AccountVerificationService:
    def __init__(self) -> None:
        self.mailer = NotificationService()

    async def send_registration_verification(self, db: AsyncSession, patient: Patient) -> None:
        token = await self._issue_token(db, patient, AccountActionPurpose.EMAIL_VERIFICATION)
        subject = "Verify your HealLink email"
        body = self._build_verification_body(token, "registration")
        self.mailer.send_email(patient.email, subject, body)

    async def verify_email(self, db: AsyncSession, token: str) -> Patient:
        try:
            record = await self._consume_token(db, token, AccountActionPurpose.EMAIL_VERIFICATION)
        except HTTPException:
            record = await self._consume_token(db, token, AccountActionPurpose.EMAIL_CHANGE)
        patient = await db.scalar(select(Patient).where(Patient.id == record.patient_id))
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        patient.is_verified = True
        patient.verification_status = "verified"
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient

    async def request_password_reset(self, db: AsyncSession, email: str) -> None:
        patient = await db.scalar(select(Patient).where(Patient.email == email.lower()))
        if not patient:
            return
        token = await self._issue_token(db, patient, AccountActionPurpose.PASSWORD_RESET)
        subject = "Reset your HealLink password"
        body = self._build_password_reset_body(token)
        self.mailer.send_email(patient.email, subject, body)

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> Patient:
        record = await self._consume_token(db, token, AccountActionPurpose.PASSWORD_RESET)
        patient = await db.scalar(select(Patient).where(Patient.id == record.patient_id))
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        patient.password_hash = hash_password(new_password)
        db.add(patient)
        await db.execute(delete(RefreshToken).where(RefreshToken.patient_id == patient.id))
        await db.commit()
        await db.refresh(patient)
        return patient

    async def request_email_change(self, db: AsyncSession, patient: Patient, new_email: str) -> None:
        token = await self._issue_token(
            db,
            patient,
            AccountActionPurpose.EMAIL_CHANGE,
            new_email=new_email.lower(),
        )
        subject = "Verify your new HealLink email"
        body = self._build_email_change_body(token, new_email.lower())
        self.mailer.send_email(new_email.lower(), subject, body)

    async def _issue_token(
        self,
        db: AsyncSession,
        patient: Patient,
        purpose: AccountActionPurpose,
        new_email: str | None = None,
    ) -> str:
        await db.execute(
            delete(AccountActionToken).where(
                AccountActionToken.patient_id == patient.id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.used_at.is_(None),
            )
        )
        raw_token = token_urlsafe(32)
        record = AccountActionToken(
            patient_id=patient.id,
            purpose=purpose,
            token_hash=hash_token(raw_token),
            new_email=new_email,
            expires_at=datetime.utcnow() + timedelta(hours=settings.account_action_token_expire_hours),
            used_at=None,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        return raw_token

    async def _consume_token(
        self,
        db: AsyncSession,
        token: str,
        purpose: AccountActionPurpose,
    ) -> AccountActionToken:
        token_hash_value = hash_token(token)
        record = await db.scalar(
            select(AccountActionToken).where(
                AccountActionToken.token_hash == token_hash_value,
                AccountActionToken.purpose == purpose,
            )
        )
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        if record.used_at is not None or record.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        record.used_at = datetime.utcnow()
        db.add(record)
        await db.commit()
        return record

    def _build_verification_body(self, token: str, reason: str) -> str:
        return (
            f"Your HealLink email verification token for {reason} is:\n\n"
            f"{token}\n\n"
            f"Use it with POST /api/v1/auth/verify-email before it expires."
        )

    def _build_password_reset_body(self, token: str) -> str:
        return (
            "Your HealLink password reset token is:\n\n"
            f"{token}\n\n"
            "Use it with POST /api/v1/auth/reset-password before it expires."
        )

    def _build_email_change_body(self, token: str, new_email: str) -> str:
        return (
            f"A request was made to change your HealLink email to {new_email}.\n\n"
            f"Verification token:\n{token}\n\n"
            "Use it with POST /api/v1/auth/verify-email before it expires."
        )