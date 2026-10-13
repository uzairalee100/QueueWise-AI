"""
QueueWise AI — Counter ORM Model and Association Table
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    DateTime,
    Enum as SQLEnum,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import CounterStatus

# Association table between Counter and ServiceCategory
counter_services = Table(
    "counter_services",
    Base.metadata,
    Column(
        "counter_id",
        Uuid(as_uuid=True),
        ForeignKey("counters.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "service_category_id",
        Uuid(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Counter(Base):
    """Physical or virtual service counter/window."""
    __tablename__ = "counters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[CounterStatus] = mapped_column(
        SQLEnum(CounterStatus, name="counter_status_enum"),
        default=CounterStatus.CLOSED,
        nullable=False,
    )
    assigned_operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_token_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="SET NULL", use_alter=True, name="fk_counter_current_token"),
        nullable=True,
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    operator = relationship("User", back_populates="counters")
    supported_services = relationship(
        "ServiceCategory",
        secondary=counter_services,
        back_populates="counters",
        lazy="selectin",
    )
    current_token = relationship(
        "Token",
        foreign_keys=[current_token_id],
        post_update=True,
        lazy="joined",
    )
    service_events = relationship("ServiceEvent", back_populates="counter")

    @property
    def current_token_display_number(self) -> Optional[str]:
        return self.current_token.display_number if self.current_token else None
