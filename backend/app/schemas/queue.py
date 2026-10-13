"""
QueueWise AI — Queue Schemas

Data transfer objects for queue summary metrics, real-time counter status,
and dynamic wait-time estimation.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ServingTokenInfo(BaseModel):
    """Information about a token currently being served at a counter."""
    counter_id: uuid.UUID
    counter_name: str
    token_id: uuid.UUID
    token_display_number: str
    service_started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QueueSummaryItem(BaseModel):
    """Real-time operational summary for a single service category."""
    service_id: uuid.UUID
    service_name: str
    service_code: str
    waiting_count: int = 0
    serving_count: int = 0
    completed_count: int = 0
    skipped_count: int = 0
    cancelled_count: int = 0
    active_counters: int = 0
    total_counters: int = 0
    avg_service_duration_seconds: int = 180
    estimated_wait_for_next_arrival: int = 0
    is_stalled: bool = False
    queue_status: str = "NORMAL"  # "NORMAL" | "BUSY" | "CONGESTED" | "STALLED"
    next_token_display_number: Optional[str] = None
    currently_serving: List[ServingTokenInfo] = []

    model_config = ConfigDict(from_attributes=True)


class QueueSummaryResponse(BaseModel):
    """System-wide queue status overview across all service categories."""
    session_id: str
    timestamp: datetime
    total_waiting: int = 0
    total_serving: int = 0
    total_active_counters: int = 0
    services: List[QueueSummaryItem] = []

    model_config = ConfigDict(from_attributes=True)


class WaitEstimateDetail(BaseModel):
    """Detailed breakdown of wait-time estimation."""
    service_id: uuid.UUID
    service_name: str
    service_code: str
    position_ahead: int
    active_counters: int
    avg_service_duration_seconds: int
    estimated_wait_seconds: int
    estimated_wait_minutes: float
    is_stalled: bool
    calculation_basis: str  # "HISTORICAL_WINDOW" | "CONFIGURED_DEFAULT" | "FALLBACK_DEFAULT"
    confidence_level: str  # "HIGH" | "MEDIUM" | "LOW"
    status_message: str

    model_config = ConfigDict(from_attributes=True)
