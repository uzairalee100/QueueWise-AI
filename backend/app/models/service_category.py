"""
QueueWise AI — Service Category ORM Model
"""
import uuid
from datetime import datetime, timezone
from typing import List
from sqlalchemy import String, Integer, Boolean, DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ServiceCategory(Base):
    """Categorization of services offered by an institution (e.g. Cashier, Registration)."""
    __tablename__ = "service_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    default_duration_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    priority_policy: Mapped[str] = mapped_column(String(50), default="FIFO", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    tokens = relationship("Token", back_populates="service_category")
    counters = relationship(
        "Counter",
        secondary="counter_services",
        back_populates="supported_services",
    )
