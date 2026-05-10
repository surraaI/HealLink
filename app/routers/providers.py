from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.appointment import ServiceCatalogResponse
from app.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderServiceCreate,
    ServiceSlotCreate,
    ServiceSlotResponse,
)
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["Providers"])
provider_service = ProviderService()


@router.get("", response_model=list[ProviderResponse])
def list_providers(
    db: Annotated[Session, Depends(get_db)],
    provider_type: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
) -> list[ProviderResponse]:
    providers = provider_service.list_providers(db, provider_type=provider_type, location=location)
    return [ProviderResponse.model_validate(item) for item in providers]


@router.post("", response_model=ProviderResponse)
def register_provider(
    payload: ProviderCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderResponse:
    provider = provider_service.create_provider(db, payload)
    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/services", response_model=ServiceCatalogResponse)
def create_provider_service(
    provider_id: int,
    payload: ProviderServiceCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceCatalogResponse:
    service = provider_service.create_service(db, provider_id, payload)
    return ServiceCatalogResponse.model_validate(service)


@router.post("/services/{service_id}/slots", response_model=ServiceSlotResponse)
def create_service_slot(
    service_id: int,
    payload: ServiceSlotCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceSlotResponse:
    slot = provider_service.create_service_slot(db, service_id, payload)
    return ServiceSlotResponse.model_validate(slot)


@router.get("/services/{service_id}/slots", response_model=list[ServiceSlotResponse])
def list_service_slots(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    only_available: bool = True,
) -> list[ServiceSlotResponse]:
    slots = provider_service.list_service_slots(db, service_id=service_id, only_available=only_available)
    return [ServiceSlotResponse.model_validate(item) for item in slots]
