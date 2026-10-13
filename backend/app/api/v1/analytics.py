"""
QueueWise AI — Operational Analytics REST API Endpoints

Provides REST endpoints for supervisors and operators to monitor:
- Summary queue KPIs (throughput, average waits, SLA compliance)
- Hourly volume trends
- Service category breakdowns
- Physical counter efficiency
- Audit event feed from stored ServiceEvent records
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    AnalyticsSummary,
    HourlyTrafficPoint,
    ServiceAnalyticsItem,
    CounterAnalyticsItem,
    ServiceEventLogItem,
    OperationalAnalyticsResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary, summary="Get summary queue operational metrics")
async def get_analytics_summary(
    hours_back: Optional[int] = Query(None, description="Filter to last N hours (e.g. 24, 168)"),
    session_id: Optional[str] = Query(None, description="Scope to a specific session"),
    include_simulations: bool = Query(False, description="Whether to include simulated tokens"),
    sla_seconds: int = Query(600, description="Target SLA max wait threshold in seconds"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes high-level operational metrics directly from stored Token and ServiceEvent records.
    """
    start_time = None
    if hours_back:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return await AnalyticsService.get_summary_metrics(
        session=db,
        start_time=start_time,
        session_id=session_id,
        include_simulations=include_simulations,
        target_sla_seconds=sla_seconds,
    )


@router.get("/hourly", response_model=List[HourlyTrafficPoint], summary="Get hourly arrival and completion trends")
async def get_hourly_trends(
    hours_back: Optional[int] = Query(24, description="Filter window (defaults to 24h)"),
    session_id: Optional[str] = Query(None, description="Scope to a specific session"),
    include_simulations: bool = Query(False, description="Whether to include simulated tokens"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregates token traffic by hour of day (0..23) for volume visualization.
    """
    start_time = None
    if hours_back:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return await AnalyticsService.get_hourly_trends(
        session=db,
        start_time=start_time,
        session_id=session_id,
        include_simulations=include_simulations,
    )


@router.get("/services", response_model=List[ServiceAnalyticsItem], summary="Get service category metrics breakdown")
async def get_service_performance(
    hours_back: Optional[int] = Query(None, description="Filter window in hours"),
    session_id: Optional[str] = Query(None, description="Scope to a specific session"),
    include_simulations: bool = Query(False, description="Whether to include simulated tokens"),
    sla_seconds: int = Query(600, description="Target SLA threshold"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes wait times, completion rates, and SLA compliance per service category.
    """
    start_time = None
    if hours_back:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return await AnalyticsService.get_service_performance(
        session=db,
        start_time=start_time,
        session_id=session_id,
        include_simulations=include_simulations,
        target_sla_seconds=sla_seconds,
    )


@router.get("/counters", response_model=List[CounterAnalyticsItem], summary="Get counter desk efficiency metrics")
async def get_counter_performance(
    hours_back: Optional[int] = Query(None, description="Filter window in hours"),
    include_simulations: bool = Query(False, description="Whether to include simulated tokens"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes tokens served, service duration, and utilization per physical counter.
    """
    start_time = None
    if hours_back:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return await AnalyticsService.get_counter_performance(
        session=db,
        start_time=start_time,
        include_simulations=include_simulations,
    )


@router.get("/events", response_model=List[ServiceEventLogItem], summary="Get audit event feed")
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200, description="Max event records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves recent operational events directly from the immutable ServiceEvent table.
    """
    return await AnalyticsService.get_recent_service_events(session=db, limit=limit)


@router.get("/dashboard", response_model=OperationalAnalyticsResponse, summary="Get unified analytics dashboard")
async def get_unified_dashboard(
    hours_back: Optional[int] = Query(None, description="Filter window in hours"),
    session_id: Optional[str] = Query(None, description="Scope to a specific session"),
    include_simulations: bool = Query(False, description="Whether to include simulated tokens"),
    sla_seconds: int = Query(600, description="Target SLA threshold"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregates all analytics subsystems into a single comprehensive payload for the dashboard UI.
    """
    start_time = None
    if hours_back:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return await AnalyticsService.get_full_dashboard(
        session=db,
        start_time=start_time,
        session_id=session_id,
        include_simulations=include_simulations,
        target_sla_seconds=sla_seconds,
    )
