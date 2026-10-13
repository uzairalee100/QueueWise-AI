"""
QueueWise AI — Notification Schemas
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import NotificationType, NotificationChannel, NotificationStatus


class NotificationResponse(BaseModel):
    """Notification response returned to client."""
    id: uuid.UUID
    token_id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel
    status: NotificationStatus
    title: Optional[str] = None
    message: str
    created_at: datetime
    sent_at: Optional[datetime] = None
    retry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    """Payload to trigger a notification dispatch."""
    token_id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel = NotificationChannel.IN_APP
    title: Optional[str] = Field(None, max_length=100)
    message: str = Field(..., max_length=255)
