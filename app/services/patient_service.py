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
        full_name = payload.full_name
        if not full_name and payload.first_name and payload.last_name:
            full_name = f"{payload.first_name.strip()} {payload.last_name.strip()}".strip()
        if not full_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full_name or first_name and last_name are required",
            )
        patient = Patient(
            email=payload.email.lower(),
            full_name=full_name.strip(),
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
