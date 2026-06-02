from datetime import datetime, timedelta
from secrets import randbelow, token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, hash_token
from app.models.account_action_token import AccountActionPurpose, AccountActionToken
from app.models.patient import Patient
from app.models.provider import Provider
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

    async def send_provider_registration_verification(self, db: AsyncSession, provider: Provider) -> None:
        token = await self._issue_token_for_provider(db, provider, AccountActionPurpose.EMAIL_VERIFICATION)
        subject = "Verify your HealLink provider email"
        body = self._build_verification_body(token, "provider registration")
        self.mailer.send_email(provider.email, subject, body)

    async def resend_verification(self, db: AsyncSession, email: str) -> None:
        """Resend verification code to an unverified user."""
        patient = await db.scalar(select(Patient).where(Patient.email == email.lower()))
        if not patient:
            # Don't reveal if email exists for security
            return
        if patient.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )
        token = await self._issue_token(db, patient, AccountActionPurpose.EMAIL_VERIFICATION)
        subject = "Verify your HealLink email"
        body = self._build_verification_body(token, "registration")
        self.mailer.send_email(patient.email, subject, body)

    async def resend_provider_verification(self, db: AsyncSession, email: str) -> None:
        """Resend verification code to an unverified provider."""
        provider = await db.scalar(select(Provider).where(Provider.email == email.lower()))
        if not provider:
            # Don't reveal if email exists for security
            return
        if provider.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )
        token = await self._issue_token_for_provider(db, provider, AccountActionPurpose.EMAIL_VERIFICATION)
        subject = "Verify your HealLink provider email"
        body = self._build_verification_body(token, "provider registration")
        self.mailer.send_email(provider.email, subject, body)

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

    async def verify_provider_email(self, db: AsyncSession, token: str) -> Provider:
        try:
            record = await self._consume_token_for_provider(db, token, AccountActionPurpose.EMAIL_VERIFICATION)
        except HTTPException:
            record = await self._consume_token_for_provider(db, token, AccountActionPurpose.EMAIL_CHANGE)
        provider = await db.scalar(select(Provider).where(Provider.id == record.provider_id))
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        provider.is_verified = True
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        return provider

    async def request_password_reset(self, db: AsyncSession, email: str) -> None:
        patient = await db.scalar(select(Patient).where(Patient.email == email.lower()))
        if not patient:
            return
        token = await self._issue_token(db, patient, AccountActionPurpose.PASSWORD_RESET)
        subject = "Reset your HealLink password"
        body = self._build_password_reset_body(token)
        self.mailer.send_email(patient.email, subject, body)

    async def request_provider_password_reset(self, db: AsyncSession, email: str) -> None:
        provider = await db.scalar(select(Provider).where(Provider.email == email.lower()))
        if not provider:
            return
        token = await self._issue_token_for_provider(db, provider, AccountActionPurpose.PASSWORD_RESET)
        subject = "Reset your HealLink provider password"
        body = self._build_password_reset_body(token)
        self.mailer.send_email(provider.email, subject, body)

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

    async def reset_provider_password(self, db: AsyncSession, token: str, new_password: str) -> Provider:
        record = await self._consume_token_for_provider(db, token, AccountActionPurpose.PASSWORD_RESET)
        provider = await db.scalar(select(Provider).where(Provider.id == record.provider_id))
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        provider.hashed_password = hash_password(new_password)
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        return provider

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

    async def request_provider_email_change(self, db: AsyncSession, provider: Provider, new_email: str) -> None:
        token = await self._issue_token_for_provider(
            db,
            provider,
            AccountActionPurpose.EMAIL_CHANGE,
            new_email=new_email.lower(),
        )
        subject = "Verify your new HealLink provider email"
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
        raw_token = self._generate_code(purpose)
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

    async def _issue_token_for_provider(
        self,
        db: AsyncSession,
        provider: Provider,
        purpose: AccountActionPurpose,
        new_email: str | None = None,
    ) -> str:
        await db.execute(
            delete(AccountActionToken).where(
                AccountActionToken.provider_id == provider.id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.used_at.is_(None),
            )
        )
        raw_token = self._generate_code(purpose)
        record = AccountActionToken(
            provider_id=provider.id,
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
                AccountActionToken.patient_id.is_not(None),
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

    async def _consume_token_for_provider(
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
                AccountActionToken.provider_id.is_not(None),
            )
        )
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        if record.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        if record.used_at is not None:
            if purpose == AccountActionPurpose.EMAIL_VERIFICATION:
                provider = await db.scalar(select(Provider).where(Provider.id == record.provider_id))
                if provider and not provider.is_verified:
                    return record
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        record.used_at = datetime.utcnow()
        db.add(record)
        await db.commit()
        return record

    def _build_verification_body(self, token: str, reason: str) -> str:
        return (
            f"Hi,\n\n"
            f"Thanks for starting your {reason} with HealLink. To complete the process, please enter the 6-digit verification code below.\n\n"
            f"Verification code: {token}\n\n"
            f"This code expires in {settings.account_action_token_expire_hours} hours.\n\n"
            "If you did not request this, you can safely ignore this message.\n\n"
            "Thanks,\nThe HealLink team"
        )

    def _build_password_reset_body(self, token: str) -> str:
        return (
            "Hi,\n\n"
            "We received a request to reset your HealLink password. Use the code below to set a new password.\n\n"
            f"Password reset code:\n{token}\n\n"
            f"This code expires in {settings.account_action_token_expire_hours} hours.\n\n"
            "If you didn't request a password reset, please ignore this email or contact support.\n\n"
            "Thanks,\nThe HealLink team"
        )

    def _build_email_change_body(self, token: str, new_email: str) -> str:
        return (
            f"Hi,\n\n"
            f"A request was made to change your HealLink account email to {new_email}. To confirm this change, please enter the 6-digit verification code below.\n\n"
            f"Verification code: {token}\n\n"
            f"This code expires in {settings.account_action_token_expire_hours} hours.\n\n"
            "If you did not request this change, you can ignore this message or contact support.\n\n"
            "Thanks,\nThe HealLink team"
        )

    def _generate_code(self, purpose: AccountActionPurpose) -> str:
        if purpose in {AccountActionPurpose.EMAIL_VERIFICATION, AccountActionPurpose.EMAIL_CHANGE}:
            return f"{randbelow(1_000_000):06d}"
        return token_urlsafe(32)
