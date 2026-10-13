"""
QueueWise AI — Simulation Run ORM Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Enum as SQLEnum,
    Uuid,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import SimulationStatus


class SimulationRun(Base):
    """Isolated scenario execution for testing queue optimizations."""
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scenario_config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[SimulationStatus] = mapped_column(
        SQLEnum(SimulationStatus, name="simulation_status_enum"),
        default=SimulationStatus.CREATED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    tokens = relationship("Token", back_populates="simulation_run")
