from datetime import datetime, timezone

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import ServiceCatalog
from app.models.provider import Provider, ProviderType, ServiceSlot
from app.schemas.provider import ProviderCreate, ProviderServiceCreate, ServiceSlotCreate
from app.services.notification_service import NotificationService
from app.services.storage_service import upload_license_document


class ProviderService:
    async def list_providers(self, db: AsyncSession, provider_type: str | None, location: str | None) -> list[Provider]:
        statement = select(Provider)
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
        provider = Provider(
            name=payload.name.strip(),
            provider_type=provider_type,  # type: ignore[arg-type]
            email=payload.email.lower(),
            phone=payload.phone,
            location=payload.location.strip(),
            description=payload.description,
        )
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        return provider

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

    provider = Provider(
        name=form_data.name.strip(),
        provider_type=provider_type,  # type: ignore[arg-type]
        email=form_data.email.lower(),
        phone=form_data.phone,
        location=form_data.location.strip(),
        description=form_data.description,
        verification_status="pending",
        license_document_url=secure_url,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    # Notify super admin(s) — create admin-scoped notification
    try:
        note_svc = NotificationService()
        await note_svc.stage_admin_event(db, title="New provider pending verification", body=f"{provider.name} ({provider.provider_type}) has submitted registration for review.")
        await db.commit()
    except Exception:
        # don't fail registration if notification fails
        pass

    return provider


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
    # TODO: send email to provider
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
