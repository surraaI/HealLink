from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.account_action_token import AccountActionToken
from app.models.patient import Patient
from app.models.refresh_token import RefreshToken
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    async def get_by_email(self, db: AsyncSession, email: str) -> Patient | None:
        statement = select(Patient).where(Patient.email == email)
        return await db.scalar(statement)

    async def get_by_id(self, db: AsyncSession, patient_id: int) -> Patient | None:
        statement = select(Patient).where(Patient.id == patient_id)
        return await db.scalar(statement)

    async def create_patient(self, db: AsyncSession, payload: PatientCreate) -> Patient:
        # require at least a first name or last name
        if not payload.first_name and not payload.last_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name or last_name is required",
            )
        first_name = payload.first_name.strip() if payload.first_name else None
        last_name = payload.last_name.strip() if payload.last_name else None
        patient = Patient(
            email=payload.email.lower(),
            first_name=first_name,
            last_name=last_name,
            phone_number=payload.phone_number.strip() if payload.phone_number else None,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender.strip() if payload.gender else None,
            role=payload.role,
            password_hash=hash_password(payload.password),
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Patient | None:
        patient = await self.get_by_email(db, email.lower())
        if not patient:
            return None
        if not verify_password(password, patient.password_hash):
            return None
        if not patient.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
        if not patient.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in")
        return patient

    async def deactivate_patient(self, db: AsyncSession, patient: Patient) -> None:
        patient.is_active = False
        db.add(patient)
        await db.execute(delete(RefreshToken).where(RefreshToken.patient_id == patient.id))
        await db.execute(delete(AccountActionToken).where(AccountActionToken.patient_id == patient.id))
        await db.commit()

    async def update_patient(self, db: AsyncSession, patient: Patient, payload: PatientUpdate) -> tuple[Patient, str | None]:
        email_changed: str | None = None
        if payload.email and payload.email.lower() != patient.email:
            existing = await self.get_by_email(db, payload.email.lower())
            if existing and existing.id != patient.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
            patient.email = payload.email.lower()
            patient.is_verified = False
            patient.verification_status = "pending"
            email_changed = patient.email

        if payload.first_name is not None:
            patient.first_name = payload.first_name.strip() or None
        if payload.last_name is not None:
            patient.last_name = payload.last_name.strip() or None
        if payload.phone_number is not None:
            patient.phone_number = payload.phone_number.strip() or None
        if payload.date_of_birth is not None:
            patient.date_of_birth = payload.date_of_birth
        if payload.gender is not None:
            patient.gender = payload.gender.strip() or None

        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient, email_changed
