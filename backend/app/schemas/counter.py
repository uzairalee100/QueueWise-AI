"""
QueueWise AI — Counter Schemas
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import CounterStatus
from app.schemas.service import ServiceCategoryResponse


class CounterBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)


class CounterCreate(CounterBase):
    supported_service_ids: List[uuid.UUID] = []


class CounterStatusUpdate(BaseModel):
    status: CounterStatus


class CounterAssignOperator(BaseModel):
    operator_id: Optional[uuid.UUID] = None


class CounterResponse(CounterBase):
    id: uuid.UUID
    status: CounterStatus
    assigned_operator_id: Optional[uuid.UUID] = None
    current_token_id: Optional[uuid.UUID] = None
    status_changed_at: datetime
    created_at: datetime
    supported_services: List[ServiceCategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)
