from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.appointment import ServiceCatalog
from app.models.provider import Provider, ProviderType, ServiceSlot
from app.schemas.provider import ProviderCreate, ProviderServiceCreate, ServiceSlotCreate


class ProviderService:
    def list_providers(self, db: Session, provider_type: str | None, location: str | None) -> list[Provider]:
        statement: Select[tuple[Provider]] = select(Provider)
        if provider_type:
            statement = statement.where(Provider.provider_type == provider_type)
        if location:
            statement = statement.where(Provider.location.ilike(f"%{location}%"))
        statement = statement.order_by(Provider.created_at.desc())
        return list(db.scalars(statement).all())

    def create_provider(self, db: Session, payload: ProviderCreate) -> Provider:
        existing = db.scalar(select(Provider).where(Provider.email == payload.email.lower()))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider email already exists",
            )
        provider_type = payload.provider_type.strip().upper()
        if provider_type not in {item.value for item in ProviderType}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid provider_type",
            )
        provider = Provider(
            name=payload.name.strip(),
            provider_type=provider_type,  # type: ignore[arg-type]
            email=payload.email.lower(),
            phone=payload.phone,
            location=payload.location.strip(),
            description=payload.description,
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def create_service(self, db: Session, provider_id: int, payload: ProviderServiceCreate) -> ServiceCatalog:
        provider = db.scalar(select(Provider).where(Provider.id == provider_id))
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

        service = ServiceCatalog(
            provider_id=provider.id,
            name=payload.name.strip(),
            service_type=payload.service_type.strip(),
            location=payload.location.strip(),
            price=payload.price,
            duration_minutes=payload.duration_minutes,
            description=payload.description,
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    def create_service_slot(self, db: Session, service_id: int, payload: ServiceSlotCreate) -> ServiceSlot:
        service = db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == service_id))
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        starts_at = payload.starts_at.replace(tzinfo=None) if payload.starts_at.tzinfo else payload.starts_at
        ends_at = payload.ends_at.replace(tzinfo=None) if payload.ends_at.tzinfo else payload.ends_at
        if starts_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot start time must be in the future",
            )
        if ends_at <= starts_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slot end time must be after start time",
            )

        conflict = db.scalar(
            select(ServiceSlot)
            .where(ServiceSlot.service_id == service_id)
            .where(ServiceSlot.starts_at < ends_at)
            .where(ServiceSlot.ends_at > starts_at)
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot overlaps with an existing slot",
            )

        slot = ServiceSlot(service_id=service_id, starts_at=starts_at, ends_at=ends_at, is_booked=False)
        db.add(slot)
        db.commit()
        db.refresh(slot)
        return slot

    def list_service_slots(self, db: Session, service_id: int, only_available: bool) -> list[ServiceSlot]:
        statement = select(ServiceSlot).where(ServiceSlot.service_id == service_id).order_by(ServiceSlot.starts_at)
        if only_available:
            statement = statement.where(ServiceSlot.is_booked.is_(False))
        return list(db.scalars(statement).all())
