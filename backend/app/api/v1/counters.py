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
from app.core.websocket import ws_manager
from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.enums import CounterStatus, ServiceEventType
from app.models.service_event import ServiceEvent
from app.models.audit_log import AuditLog
from app.schemas.counter import (
    CounterCreate,
    CounterResponse,
    CounterStatusUpdate,
    CounterAssignOperator,
    CounterAssignServices,
)
from app.schemas.token import TokenResponse
from app.services.queue_engine import (
    QueueEngine,
    CounterNotFoundError,
    CounterUnavailableError,
    TokenNotFoundError,
    InvalidStateTransitionError,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=List[CounterResponse])
async def list_counters(
    db: AsyncSession = Depends(get_db),
):
    """List all counters with their supported services and current status."""
    stmt = (
        select(Counter)
        .options(selectinload(Counter.supported_services), selectinload(Counter.current_token))
        .order_by(Counter.name.asc())
    )
    result = await db.execute(stmt)
    counters = result.scalars().all()
    return list(counters)


@router.get("/{counter_id}", response_model=CounterResponse)
async def get_counter(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get single counter details."""
    counter = await db.get(
        Counter,
        counter_id,
        options=[selectinload(Counter.supported_services), selectinload(Counter.current_token)],
    )
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counter '{counter_id}' not found.",
        )
    return counter


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
        Counter,
        counter_id,
        options=[selectinload(Counter.supported_services), selectinload(Counter.current_token)],
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
    db.add(event)

    audit = AuditLog(
        action="UPDATE_COUNTER_STATUS",
        target_entity="Counter",
        target_id=str(counter.id),
        outcome="SUCCESS",
        metadata_json={"old_status": old_status.value, "new_status": payload.status.value},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(counter)

    # Multicast real-time counter status change
    await ws_manager.broadcast(
        event="COUNTER_STATUS_CHANGED",
        data={
            "counter_id": str(counter.id),
            "counter_name": counter.name,
            "old_status": old_status.value,
            "status": counter.status.value,
        },
    )

    return counter


@router.post("/{counter_id}/open", response_model=CounterResponse)
async def open_counter(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Operator action: Open counter for service."""
    status_to_set = CounterStatus.OPEN_IDLE
    counter = await db.get(
        Counter,
        counter_id,
        options=[selectinload(Counter.supported_services), selectinload(Counter.current_token)],
    )
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")
    if counter.current_token_id:
        status_to_set = CounterStatus.OPEN_SERVING

    return await update_counter_status(counter_id, CounterStatusUpdate(status=status_to_set), db)


@router.post("/{counter_id}/pause", response_model=CounterResponse)
async def pause_counter(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Operator action: Temporarily pause counter (e.g. break)."""
    return await update_counter_status(counter_id, CounterStatusUpdate(status=CounterStatus.PAUSED), db)


@router.post("/{counter_id}/resume", response_model=CounterResponse)
async def resume_counter(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Operator action: Resume counter from pause."""
    return await update_counter_status(counter_id, CounterStatusUpdate(status=CounterStatus.OPEN_IDLE), db)


@router.post("/{counter_id}/close", response_model=CounterResponse)
async def close_counter(
    counter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Operator action: Close counter for end of shift or maintenance."""
    return await update_counter_status(counter_id, CounterStatusUpdate(status=CounterStatus.CLOSED), db)


@router.patch("/{counter_id}/operator", response_model=CounterResponse)
async def assign_operator(
    counter_id: uuid.UUID,
    payload: CounterAssignOperator,
    db: AsyncSession = Depends(get_db),
):
    """Assign or unassign a staff operator to this counter."""
    counter = await db.get(
        Counter,
        counter_id,
        options=[selectinload(Counter.supported_services), selectinload(Counter.current_token)],
    )
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")

    counter.assigned_operator_id = payload.operator_id
    now = datetime.now(timezone.utc)

    event = ServiceEvent(
        token_id=None,
        counter_id=counter.id,
        event_type=ServiceEventType.OPERATOR_ASSIGNED,
        timestamp=now,
        reason=f"Operator {'assigned: ' + str(payload.operator_id) if payload.operator_id else 'unassigned'}",
    )
    db.add(event)

    await db.commit()
    await db.refresh(counter)
    return counter


@router.put("/{counter_id}/services", response_model=CounterResponse)
async def update_counter_services(
    counter_id: uuid.UUID,
    payload: CounterAssignServices,
    db: AsyncSession = Depends(get_db),
):
    """Configure which service categories this counter serves."""
    counter = await db.get(
        Counter,
        counter_id,
        options=[selectinload(Counter.supported_services), selectinload(Counter.current_token)],
    )
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")

    services_stmt = select(ServiceCategory).where(
        ServiceCategory.id.in_(payload.supported_service_ids)
    )
    services_res = await db.execute(services_stmt)
    counter.supported_services = list(services_res.scalars().all())

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
        counter = await db.get(Counter, counter_id)
        if not counter:
            raise CounterNotFoundError(f"Counter '{counter_id}' not found.")

        token = await QueueEngine.call_next_token(
            session=db,
            counter_id=counter_id,
            session_id=session_id,
        )

        if token:
            # Dispatch call notification to citizen
            await NotificationService.notify_token_called(
                session=db, token=token, counter_name=counter.name
            )

            # Check and trigger approaching notifications for upcoming tokens in line
            await NotificationService.check_and_notify_approaching_tokens(
                session=db,
                service_category_id=token.service_category_id,
                session_id=session_id,
            )

            # Multicast real-time TOKEN_CALLED event
            await ws_manager.broadcast(
                event="TOKEN_CALLED",
                data={
                    "token_id": str(token.id),
                    "public_id": token.public_id,
                    "display_number": token.display_number,
                    "counter_id": str(counter.id),
                    "counter_name": counter.name,
                    "status": "CALLED",
                },
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

        # Multicast real-time TOKEN_SERVING event
        await ws_manager.broadcast(
            event="TOKEN_SERVING",
            data={
                "token_id": str(token.id),
                "public_id": token.public_id,
                "display_number": token.display_number,
                "counter_id": str(counter.id),
                "counter_name": counter.name,
                "status": "SERVING",
            },
            session_id=token.session_id,
        )

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

        # Dispatch completion notification
        await NotificationService.notify_token_completed(session=db, token=token)

        # Check and trigger approaching notifications for remaining waiting queue
        await NotificationService.check_and_notify_approaching_tokens(
            session=db,
            service_category_id=token.service_category_id,
            session_id=token.session_id,
        )

        # Multicast real-time TOKEN_COMPLETED event
        await ws_manager.broadcast(
            event="TOKEN_COMPLETED",
            data={
                "token_id": str(token.id),
                "public_id": token.public_id,
                "display_number": token.display_number,
                "counter_id": str(counter.id),
                "counter_name": counter.name,
                "status": "COMPLETED",
            },
            session_id=token.session_id,
        )

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

        # Dispatch skip notification
        await NotificationService.notify_token_skipped(session=db, token=token, reason=reason)

        # Check approaching notifications for remaining queue
        await NotificationService.check_and_notify_approaching_tokens(
            session=db,
            service_category_id=token.service_category_id,
            session_id=token.session_id,
        )

        # Multicast real-time TOKEN_SKIPPED event
        await ws_manager.broadcast(
            event="TOKEN_SKIPPED",
            data={
                "token_id": str(token.id),
                "public_id": token.public_id,
                "display_number": token.display_number,
                "counter_id": str(counter.id),
                "counter_name": counter.name,
                "status": "SKIPPED",
                "reason": reason,
            },
            session_id=token.session_id,
        )

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

        # Multicast real-time TOKEN_RECALLED event
        await ws_manager.broadcast(
            event="TOKEN_RECALLED",
            data={
                "token_id": str(token.id),
                "public_id": token.public_id,
                "display_number": token.display_number,
                "counter_id": str(counter.id),
                "counter_name": counter.name,
                "status": "WAITING",
                "reason": reason,
            },
            session_id=token.session_id,
        )

        return token
    except (TokenNotFoundError, CounterNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
