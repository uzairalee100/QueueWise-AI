"""
QueueWise AI — Service Event ORM Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Uuid,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import ServiceEventType


class ServiceEvent(Base):
    """Immutable audit log of all events occurring in the queue lifecycle."""
    __tablename__ = "service_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    counter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("counters.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    event_type: Mapped[ServiceEventType] = mapped_column(
        SQLEnum(ServiceEventType, name="service_event_type_enum"),
        index=True,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # Relationships
    token = relationship("Token", back_populates="service_events")
    counter = relationship("Counter", back_populates="service_events")
    actor = relationship("User", back_populates="service_events")
