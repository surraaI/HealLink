from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_provider, get_db
from app.models.provider import Provider
from app.schemas.analytics import (
    DailyTrendResponse,
    OverallStatsResponse,
    PeakHoursResponse,
    ServiceBreakdownResponse,
)
from app.services.analytics_service import AnalyticsService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/providers/analytics", tags=["Provider Analytics"])
analytics_service = AnalyticsService()


@router.get("/overall", response_model=OverallStatsResponse)
async def get_overall_stats(
    current_provider: Annotated[Provider, Depends(get_current_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
) -> OverallStatsResponse:
    stats = await analytics_service.get_overall_stats(db, current_provider.id, days)
    return OverallStatsResponse(**stats)


@router.get("/peak-hours", response_model=list[PeakHoursResponse])
async def get_peak_hours(
    current_provider: Annotated[Provider, Depends(get_current_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
) -> list[PeakHoursResponse]:
    peak_hours = await analytics_service.get_peak_hours(db, current_provider.id, days)
    return [PeakHoursResponse(**hour) for hour in peak_hours]


@router.get("/daily-trend", response_model=list[DailyTrendResponse])
async def get_daily_trend(
    current_provider: Annotated[Provider, Depends(get_current_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyTrendResponse]:
    trend = await analytics_service.get_daily_trend(db, current_provider.id, days)
    return [DailyTrendResponse(**day) for day in trend]


@router.get("/service-breakdown", response_model=list[ServiceBreakdownResponse])
async def get_service_breakdown(
    current_provider: Annotated[Provider, Depends(get_current_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
) -> list[ServiceBreakdownResponse]:
    breakdown = await analytics_service.get_service_breakdown(db, current_provider.id, days)
    return [ServiceBreakdownResponse(**service) for service in breakdown]
