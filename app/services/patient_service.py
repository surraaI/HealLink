from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.patient import Patient
from app.schemas.patient import PatientCreate


class PatientService:
    async def get_by_email(self, db: AsyncSession, email: str) -> Patient | None:
        statement = select(Patient).where(Patient.email == email)
        return await db.scalar(statement)

    async def get_by_id(self, db: AsyncSession, patient_id: int) -> Patient | None:
        statement = select(Patient).where(Patient.id == patient_id)
        return await db.scalar(statement)

    async def create_patient(self, db: AsyncSession, payload: PatientCreate) -> Patient:
        patient = Patient(
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
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
        return patient
