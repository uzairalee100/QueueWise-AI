"""
QueueWise AI — Operational Analytics Pydantic Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid
from pydantic import BaseModel, Field


class AnalyticsSummary(BaseModel):
    """High-level operational queue KPIs computed from stored service events."""
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_tokens_issued: int
    tokens_completed: int
    tokens_currently_waiting: int
    tokens_currently_serving: int
    tokens_skipped: int
    tokens_cancelled: int
    completion_rate_pct: float
    no_show_rate_pct: float
    cancellation_rate_pct: float
    avg_wait_seconds: int
    median_wait_seconds: int
    p95_wait_seconds: int
    max_wait_seconds: int
    avg_service_seconds: int
    target_sla_seconds: int
    sla_breach_count: int
    sla_compliance_pct: float
    active_counters_count: int
    total_counters_count: int
    avg_counter_utilization_pct: float


class HourlyTrafficPoint(BaseModel):
    """Hourly volume and queue latency point for trend visualization."""
    hour: int
    hour_label: str
    arrivals_count: int
    completed_count: int
    avg_wait_seconds: int


class ServiceAnalyticsItem(BaseModel):
    """Performance metrics aggregated for a specific service category."""
    service_id: uuid.UUID
    service_code: str
    service_name: str
    total_issued: int
    completed: int
    skipped: int
    cancelled: int
    currently_waiting: int
    avg_wait_seconds: int
    avg_service_seconds: int
    sla_compliance_pct: float


class CounterAnalyticsItem(BaseModel):
    """Operational efficiency metrics for a physical service counter."""
    counter_id: uuid.UUID
    counter_name: str
    current_status: str
    supported_services: List[str]
    tokens_served: int
    avg_service_seconds: int
    total_busy_seconds: int
    utilization_pct: float


class ServiceEventLogItem(BaseModel):
    """Detailed audit event item from ServiceEvent table."""
    id: uuid.UUID
    timestamp: datetime
    event_type: str
    token_display_number: Optional[str] = None
    counter_name: Optional[str] = None
    reason: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    extra_data: Optional[Dict[str, Any]] = None


class OperationalAnalyticsResponse(BaseModel):
    """Comprehensive analytics dashboard payload."""
    summary: AnalyticsSummary
    hourly_trends: List[HourlyTrafficPoint]
    services: List[ServiceAnalyticsItem]
    counters: List[CounterAnalyticsItem]
    recent_events: List[ServiceEventLogItem]
