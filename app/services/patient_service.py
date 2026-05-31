from fastapi import HTTPException, status
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
        return patient
