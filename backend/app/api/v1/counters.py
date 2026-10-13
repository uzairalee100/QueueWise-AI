"""
QueueWise AI — Counters API Endpoints

Counter management, operator actions, and queue progression.
"""
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.enums import CounterStatus, ServiceEventType
from app.models.service_event import ServiceEvent
from app.schemas.counter import CounterCreate, CounterResponse, CounterStatusUpdate
from app.schemas.token import TokenResponse
from app.services.queue_engine import (
    QueueEngine,
    CounterNotFoundError,
    CounterUnavailableError,
    TokenNotFoundError,
    InvalidStateTransitionError,
)

router = APIRouter()


@router.get("", response_model=List[CounterResponse])
async def list_counters(
    db: AsyncSession = Depends(get_db),
):
    """List all counters with their supported services and current status."""
    stmt = (
        select(Counter)
        .options(selectinload(Counter.supported_services))
        .order_by(Counter.name.asc())
    )
    result = await db.execute(stmt)
    counters = result.scalars().all()
    return list(counters)


@router.post("", response_model=CounterResponse, status_code=status.HTTP_201_CREATED)
async def create_counter(
    payload: CounterCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new service counter."""
    counter = Counter(name=payload.name, status=CounterStatus.OPEN_IDLE)

    if payload.supported_service_ids:
        services_stmt = select(ServiceCategory).where(
            ServiceCategory.id.in_(payload.supported_service_ids)
        )
        services_res = await db.execute(services_stmt)
        counter.supported_services = list(services_res.scalars().all())

    db.add(counter)
    await db.commit()
    await db.refresh(counter)
    return counter


@router.patch("/{counter_id}/status", response_model=CounterResponse)
async def update_counter_status(
    counter_id: uuid.UUID,
    payload: CounterStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update counter status (e.g. OPEN_IDLE, PAUSED, CLOSED)."""
    counter = await db.get(
        Counter, counter_id, options=[selectinload(Counter.supported_services)]
    )
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counter '{counter_id}' not found.",
        )

    # Invariant check: cannot close or pause if currently serving without completing
    if payload.status in (CounterStatus.CLOSED, CounterStatus.PAUSED) and counter.current_token_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot close or pause counter while serving an active token. Complete or skip the token first.",
        )

    now = datetime.now(timezone.utc)
    old_status = counter.status
    counter.status = payload.status
    counter.status_changed_at = now

    event = ServiceEvent(
        token_id=None,
        counter_id=counter.id,
        event_type=ServiceEventType.COUNTER_STATUS_CHANGED,
        timestamp=now,
        reason=f"Status changed from {old_status.value} to {payload.status.value}",
    )
    # Note: ServiceEvent token_id is non-nullable in schema if strictly token-bound,
    # so we log to audit or skip event if token_id is required. Since ServiceEvent has
    # token_id nullable=False, let's only log if we have a token or handle accordingly.

    await db.commit()
    await db.refresh(counter)
    return counter


@router.post("/{counter_id}/call-next", response_model=Optional[TokenResponse])
async def call_next_token(
    counter_id: uuid.UUID,
    session_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    """
    Operator action: Call the next waiting token to this counter.
    Returns the called token or null if no waiting tokens exist.
    """
    try:
        token = await QueueEngine.call_next_token(
            session=db,
            counter_id=counter_id,
            session_id=session_id,
        )
        return token
    except (CounterNotFoundError, TokenNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CounterUnavailableError, InvalidStateTransitionError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{counter_id}/serve", response_model=TokenResponse)
async def start_service(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Operator action: Mark the called token as actively being served.
    """
    counter = await db.get(Counter, counter_id)
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")
    if not counter.current_token_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No token currently called at this counter")

    try:
        token = await QueueEngine.start_serving(db, token_id=counter.current_token_id)
        return token
    except (TokenNotFoundError, CounterNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{counter_id}/complete", response_model=TokenResponse)
async def complete_service(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Operator action: Complete service for the current token and free counter.
    """
    counter = await db.get(Counter, counter_id)
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")
    if not counter.current_token_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No token currently being served at this counter")

    try:
        token = await QueueEngine.complete_token(db, token_id=counter.current_token_id)
        return token
    except (TokenNotFoundError, CounterNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{counter_id}/skip", response_model=TokenResponse)
async def skip_service(
    counter_id: uuid.UUID,
    reason: str = "No-show",
    db: AsyncSession = Depends(get_db),
):
    """
    Operator action: Skip current token (e.g. no-show) and free counter.
    """
    counter = await db.get(Counter, counter_id)
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")
    if not counter.current_token_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No token currently called at this counter")

    try:
        token = await QueueEngine.skip_token(db, token_id=counter.current_token_id, reason=reason)
        return token
    except (TokenNotFoundError, CounterNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{counter_id}/recall", response_model=TokenResponse)
async def recall_service(
    counter_id: uuid.UUID,
    reason: str = "Requeued to waiting",
    db: AsyncSession = Depends(get_db),
):
    """
    Operator action: Return called token back to WAITING queue and free counter.
    """
    counter = await db.get(Counter, counter_id)
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")
    if not counter.current_token_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No token currently called at this counter")

    try:
        token = await QueueEngine.recall_token(db, token_id=counter.current_token_id, reason=reason)
        return token
    except (TokenNotFoundError, CounterNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
