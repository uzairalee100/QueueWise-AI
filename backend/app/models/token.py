"""
QueueWise AI — Token ORM Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import TokenStatus


class Token(Base):
    """A digital queue token issued to a citizen."""
    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    display_number: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False
    )
    service_category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False, default="default"
    )
    status: Mapped[TokenStatus] = mapped_column(
        SQLEnum(TokenStatus, name="token_status_enum"),
        default=TokenStatus.WAITING,
        index=True,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )
    contact_info: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    called_counter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("counters.id", ondelete="SET NULL"),
        nullable=True,
    )
    simulation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    called_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    service_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    service_category = relationship(
        "ServiceCategory", back_populates="tokens", lazy="joined"
    )
    called_counter = relationship(
        "Counter",
        foreign_keys=[called_counter_id],
        lazy="joined",
    )
    service_events = relationship(
        "ServiceEvent", back_populates="token", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="token", cascade="all, delete-orphan"
    )
    simulation_run = relationship("SimulationRun", back_populates="tokens")
