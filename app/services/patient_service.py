from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.patient import Patient
from app.schemas.patient import PatientCreate


class PatientService:
    def get_by_email(self, db: Session, email: str) -> Patient | None:
        statement = select(Patient).where(Patient.email == email)
        return db.scalar(statement)

    def get_by_id(self, db: Session, patient_id: int) -> Patient | None:
        statement = select(Patient).where(Patient.id == patient_id)
        return db.scalar(statement)

    def create_patient(self, db: Session, payload: PatientCreate) -> Patient:
        patient = Patient(
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    def authenticate(self, db: Session, email: str, password: str) -> Patient | None:
        patient = self.get_by_email(db, email.lower())
        if not patient:
            return None
        if not verify_password(password, patient.password_hash):
            return None
        return patient
