"""
QueueWise AI — Token Schemas
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import TokenStatus
from app.schemas.service import ServiceCategoryResponse


class TokenCreate(BaseModel):
    """Payload to request a new token."""
    service_id: Optional[uuid.UUID] = None
    service_code: Optional[str] = Field(None, max_length=10)
    session_id: Optional[str] = Field(default="default", max_length=50)
    contact_info: Optional[str] = Field(None, max_length=100)
    idempotency_key: Optional[str] = Field(None, max_length=100)
    priority: int = Field(default=0, ge=0, le=10)


class TokenTransitionRequest(BaseModel):
    """Payload for transitioning a token's state."""
    counter_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    reason: Optional[str] = Field(None, max_length=255)


class TokenResponse(BaseModel):
    """Full token object for staff/admin views."""
    id: uuid.UUID
    public_id: str
    display_number: str
    service_category_id: uuid.UUID
    session_id: str
    status: TokenStatus
    priority: int
    idempotency_key: Optional[str] = None
    contact_info: Optional[str] = None
    called_counter_id: Optional[uuid.UUID] = None
    simulation_run_id: Optional[uuid.UUID] = None
    created_at: datetime
    called_at: Optional[datetime] = None
    service_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    service_category: Optional[ServiceCategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TokenPublicStatus(BaseModel):
    """Public, citizen-facing view of a token."""
    public_id: str
    display_number: str
    status: TokenStatus
    service_name: str
    service_code: str
    position_ahead: int = 0
    estimated_wait_seconds: int = 0
    active_counters: int = 1
    is_stalled: bool = False
    called_counter_name: Optional[str] = None
    created_at: datetime
    called_at: Optional[datetime] = None
    session_id: str

    model_config = ConfigDict(from_attributes=True)
