from datetime import datetime, timezone

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.appointment import ServiceCatalog
from app.models.provider import Provider, ProviderType, ServiceSlot
from app.schemas.provider import ProviderCreate, ProviderServiceCreate, ServiceSlotCreate
from app.services.notification_service import NotificationService
from app.services.storage_service import upload_license_document
from app.services.account_verification_service import AccountVerificationService


def _first_text(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _build_provider_registration_body(provider: Provider) -> str:
    return (
        f"Hi {provider.name},\n\n"
        "Thanks for registering as a HealLink provider. We have received your profile and license document and your account is now pending review.\n\n"
        "Our team will verify your details and update your account status once the review is complete.\n\n"
        "If you did not create this account, please ignore this message.\n\n"
        "Thanks,\nThe HealLink team"
    )


class ProviderService:
    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Provider | None:
        provider = await db.scalar(select(Provider).where(Provider.email == email.lower()))
        if provider and verify_password(password, provider.hashed_password):
            return provider
        return None

    async def list_providers(self, db: AsyncSession, provider_type: str | None, location: str | None) -> list[Provider]:
        statement = select(Provider)
        statement = statement.where(Provider.verification_status == "approved")
        if provider_type:
            statement = statement.where(Provider.provider_type == provider_type)
        if location:
            statement = statement.where(Provider.location.ilike(f"%{location}%"))
        statement = statement.order_by(Provider.created_at.desc())
        res = await db.scalars(statement)
        return list(res.all())

    async def create_provider(self, db: AsyncSession, payload: ProviderCreate) -> Provider:
        existing = await db.scalar(select(Provider).where(Provider.email == payload.email.lower()))
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
        name = _first_text(payload.name)
        location = _first_text(payload.location, payload.address)
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
        if not location:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="location is required")
        if not payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password is required")
        
        provider = Provider(
            name=name,
            provider_type=provider_type,  # type: ignore[arg-type]
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            phone=_first_text(payload.phone, payload.phone_number),
            specialization=payload.specialization,
            license_number=payload.license_number,
            tin_number=payload.tin_number,
            location=location,
            address=payload.address,
            description=payload.description,
            verification_status="pending",
        )
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        return provider

    async def create_service(self, db: AsyncSession, provider_id: int, payload: ProviderServiceCreate) -> ServiceCatalog:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Looking for provider with id {provider_id}")
        provider = await db.scalar(select(Provider).where(Provider.id == provider_id))
        if not provider:
            logger.error(f"Provider {provider_id} not found in database")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

        logger.info(f"Provider {provider_id} found, creating service")
        service = ServiceCatalog(
            provider_id=provider_id,
            name=payload.name,
            service_type=payload.service_type,
            location=payload.location,
            price=payload.price,
            duration_minutes=payload.duration_minutes,
            description=payload.description,
            is_active=True,
        )
        db.add(service)
        await db.commit()
        await db.refresh(service)
        return service

    async def create_service_slot(self, db: AsyncSession, service_id: int, payload: ServiceSlotCreate) -> ServiceSlot:
        service = await db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == service_id))
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
        slot = ServiceSlot(
            service_id=service_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            is_booked=False,
        )
        db.add(slot)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def list_service_slots(self, db: AsyncSession, service_id: int, only_available: bool = True) -> list[ServiceSlot]:
        statement = select(ServiceSlot).where(ServiceSlot.service_id == service_id)
        if only_available:
            statement = statement.where(ServiceSlot.is_booked == False)
        statement = statement.order_by(ServiceSlot.starts_at)
        res = await db.scalars(statement)
        return list(res.all())

    # other methods can be added here following async pattern


# New async-ish functions for registration and admin flows
async def register_provider_with_document(db: AsyncSession, form_data, license_file: UploadFile) -> Provider:
    # Validate and upload document
    secure_url = await upload_license_document(license_file, form_data.provider_type)

    # ensure unique email
    existing = await db.scalar(select(Provider).where(Provider.email == form_data.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider email already exists")

    provider_type = form_data.provider_type.strip().upper()
    if provider_type not in {item.value for item in ProviderType}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider_type")

    name = _first_text(getattr(form_data, "name", None))
    location = _first_text(getattr(form_data, "location", None), getattr(form_data, "address", None))
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    if not location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="location is required")
    password = getattr(form_data, "password", None)
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password is required")

    provider = Provider(
        name=name,
        provider_type=provider_type,  # type: ignore[arg-type]
        email=form_data.email.lower(),
        hashed_password=hash_password(password),
        phone=_first_text(getattr(form_data, "phone", None), getattr(form_data, "phone_number", None)),
        specialization=getattr(form_data, "specialization", None),
        license_number=getattr(form_data, "license_number", None),
        tin_number=getattr(form_data, "tin_number", None),
        location=location,
        address=getattr(form_data, "address", None),
        description=form_data.description,
        verification_status="pending",
        license_document_url=secure_url,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    # Send email verification
    verification_service = AccountVerificationService()
    await verification_service.send_provider_registration_verification(db, provider)

    # Notify super admin(s) — create admin-scoped notification
    try:
        note_svc = NotificationService()
        await note_svc.stage_admin_event(db, title="New provider pending verification", body=f"{provider.name} ({provider.provider_type}) has submitted registration for review.")
        await db.commit()
    except Exception:
        # don't fail registration if notification fails
        pass

    return provider


def _build_approval_email_body(provider: Provider) -> str:
    return (
        f"Hi {provider.name},\n\n"
        "Congratulations! Your HealLink provider account has been approved and is now active.\n\n"
        "You can now log in to your account and start offering your services to patients.\n\n"
        "If you have any questions, please don't hesitate to contact us.\n\n"
        "Thanks,\nThe HealLink team"
    )


def _build_rejection_email_body(provider: Provider, reason: str) -> str:
    return (
        f"Hi {provider.name},\n\n"
        "We regret to inform you that your HealLink provider account application has been rejected.\n\n"
        f"Reason: {reason}\n\n"
        "If you believe this is an error or would like to address the concerns mentioned, please contact our support team.\n\n"
        "Thanks,\nThe HealLink team"
    )


async def verify_provider(db: AsyncSession, provider_id: int, action: str, reason: str | None, admin_id: int) -> Provider:
    provider = await db.scalar(select(Provider).where(Provider.id == provider_id))
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if action == "approve":
        provider.verification_status = "approved"
        provider.rejection_reason = None
    else:
        provider.verification_status = "rejected"
        provider.rejection_reason = reason
    provider.verified_by = admin_id
    provider.verified_at = now
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    
    # Send email to provider
    notification_service = NotificationService()
    if action == "approve":
        email_body = _build_approval_email_body(provider)
        subject = "Your HealLink Provider Account has been Approved"
    else:
        email_body = _build_rejection_email_body(provider, reason or "No reason provided")
        subject = "Your HealLink Provider Account Application Status"
    
    notification_service.send_email(provider.email, subject, email_body)
    
    return provider


async def get_providers_by_status(db: AsyncSession, status: str | None) -> list[Provider]:
    stmt = select(Provider)
    if status:
        stmt = stmt.where(Provider.verification_status == status)
    stmt = stmt.order_by(Provider.created_at.desc())
    res = await db.scalars(stmt)
    return list(res.all())


async def get_provider_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count()).select_from(Provider)) or 0
    pending = await db.scalar(select(func.count()).select_from(Provider).where(Provider.verification_status == "pending")) or 0
    approved = await db.scalar(select(func.count()).select_from(Provider).where(Provider.verification_status == "approved")) or 0
    rejected = await db.scalar(select(func.count()).select_from(Provider).where(Provider.verification_status == "rejected")) or 0
    return {"pending": int(pending), "approved": int(approved), "rejected": int(rejected), "total": int(total)}
