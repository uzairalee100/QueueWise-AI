"""
QueueWise AI — Audit Log ORM Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Uuid,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AuditLog(Base):
    """System-level and security audit log entries."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    metadata_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # Relationship
    actor = relationship("User")
