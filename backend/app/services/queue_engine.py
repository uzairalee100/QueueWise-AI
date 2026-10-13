"""
QueueWise AI — Core Queue Engine

Authoritative implementation of queue ordering, token issuance,
idempotency checking, state machine transitions, and operational invariants.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    TokenStatus,
    CounterStatus,
    ServiceEventType,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from app.models.token import Token
from app.models.service_category import ServiceCategory
from app.models.counter import Counter
from app.models.service_event import ServiceEvent
from app.models.notification import Notification
from app.core.logging import get_logger

logger = get_logger(__name__)


# --- Domain Exceptions ---

class QueueEngineError(Exception):
    """Base exception for all queue engine errors."""
    pass


class TokenNotFoundError(QueueEngineError):
    """Raised when a requested token does not exist."""
    pass


class ServiceCategoryNotFoundError(QueueEngineError):
    """Raised when a requested service category does not exist or is inactive."""
    pass


class CounterNotFoundError(QueueEngineError):
    """Raised when a requested counter does not exist."""
    pass


class CounterUnavailableError(QueueEngineError):
    """Raised when an operation cannot be performed because of counter status."""
    pass


class InvalidStateTransitionError(QueueEngineError):
    """Raised when an illegal token state transition is attempted."""
    def __init__(self, current_status: TokenStatus, target_status: TokenStatus, message: str = ""):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            message or f"Illegal transition from '{current_status.value}' to '{target_status.value}'"
        )


# --- Allowed State Machine Transitions ---
# Source of truth: PRD Section 8 & Architecture Summary
VALID_TRANSITIONS = {
    TokenStatus.WAITING: {
        TokenStatus.CALLED,
        TokenStatus.SKIPPED,
        TokenStatus.CANCELLED,
    },
    TokenStatus.CALLED: {
        TokenStatus.SERVING,
        TokenStatus.WAITING,    # recall / requeue
        TokenStatus.SKIPPED,    # no-show
    },
    TokenStatus.SERVING: {
        TokenStatus.COMPLETED,
    },
    TokenStatus.COMPLETED: set(),  # Terminal state
    TokenStatus.SKIPPED: set(),    # Terminal state
    TokenStatus.CANCELLED: set(),  # Terminal state
}


class QueueEngine:
    """Core Queue Engine providing transactional, deterministic queue operations."""

    @staticmethod
    def generate_public_id() -> str:
        """Generate a cryptographically random, URL-safe public token identifier."""
        return secrets.token_urlsafe(16)[:24]

    @classmethod
    async def create_token(
        cls,
        session: AsyncSession,
        service_category_id: Optional[uuid.UUID] = None,
        service_code: Optional[str] = None,
        session_id: str = "default",
        contact_info: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        priority: int = 0,
        simulation_run_id: Optional[uuid.UUID] = None,
    ) -> Token:
        """
        Create and issue a new queue token with duplicate request (idempotency) protection.
        """
        # 1. Idempotency Check: if key provided, check for existing token in this session
        if idempotency_key:
            stmt = select(Token).where(
                and_(
                    Token.idempotency_key == idempotency_key,
                    Token.session_id == session_id,
                )
            ).options(selectinload(Token.service_category))
            result = await session.execute(stmt)
            existing_token = result.scalar_one_or_none()
            if existing_token:
                logger.info(
                    "idempotent_token_retrieved",
                    token_id=str(existing_token.id),
                    public_id=existing_token.public_id,
                    idempotency_key=idempotency_key,
                )
                return existing_token

        # 2. Resolve Service Category
        if service_category_id:
            service = await session.get(ServiceCategory, service_category_id)
        elif service_code:
            stmt = select(ServiceCategory).where(
                and_(
                    ServiceCategory.code == service_code.upper(),
                    ServiceCategory.is_active == True,
                )
            )
            result = await session.execute(stmt)
            service = result.scalar_one_or_none()
        else:
            raise ServiceCategoryNotFoundError("Either service_category_id or service_code must be provided.")

        if not service or not service.is_active:
            raise ServiceCategoryNotFoundError("Service category not found or is currently inactive.")

        # 3. Generate sequential display number for this service & session (e.g. REG-001)
        count_stmt = select(func.count(Token.id)).where(
            and_(
                Token.service_category_id == service.id,
                Token.session_id == session_id,
            )
        )
        count_result = await session.execute(count_stmt)
        token_count = count_result.scalar() or 0
        display_number = f"{service.code}-{token_count + 1:03d}"

        # 4. Create Token entity
        public_id = cls.generate_public_id()
        now = datetime.now(timezone.utc)

        token = Token(
            public_id=public_id,
            display_number=display_number,
            service_category_id=service.id,
            session_id=session_id,
            status=TokenStatus.WAITING,
            priority=priority,
            idempotency_key=idempotency_key,
            contact_info=contact_info,
            simulation_run_id=simulation_run_id,
            created_at=now,
        )
        session.add(token)
        await session.flush()

        # 5. Record ServiceEvent
        event = ServiceEvent(
            token_id=token.id,
            event_type=ServiceEventType.TOKEN_CREATED,
            timestamp=now,
            reason="Token issued to citizen",
            extra_data={"display_number": display_number, "priority": priority},
        )
        session.add(event)

        # 6. Record Notification
        notification = Notification(
            token_id=token.id,
            type=NotificationType.CREATED,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            title="Token Issued",
            message=f"Your token is {display_number}. Please wait for your turn.",
            created_at=now,
            sent_at=now,
        )
        session.add(notification)

        await session.commit()
        await session.refresh(token)
        # Ensure service_category is loaded
        token.service_category = service

        logger.info(
            "token_created",
            token_id=str(token.id),
            public_id=token.public_id,
            display_number=token.display_number,
            service=service.code,
        )
        return token

    @classmethod
    async def get_token_by_public_id(
        cls,
        session: AsyncSession,
        public_id: str,
    ) -> Token:
        """Fetch token by public identifier with joined relationships."""
        stmt = (
            select(Token)
            .where(Token.public_id == public_id)
            .options(
                selectinload(Token.service_category),
                selectinload(Token.called_counter),
            )
        )
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        if not token:
            raise TokenNotFoundError(f"Token with public ID '{public_id}' not found.")
        return token

    @classmethod
    async def get_queue_position_and_ahead(
        cls,
        session: AsyncSession,
        token: Token,
    ) -> Tuple[int, int]:
        """
        Calculate position in queue and number of tokens ahead.
        Position is 1-indexed. Ahead is position - 1.
        Returns (position, ahead_count). If token is not WAITING, returns (0, 0).
        """
        if token.status != TokenStatus.WAITING:
            return (0, 0)

        # Count tokens WAITING in same service category and session with:
        # higher priority OR same priority and earlier created_at
        stmt = select(func.count(Token.id)).where(
            and_(
                Token.service_category_id == token.service_category_id,
                Token.session_id == token.session_id,
                Token.status == TokenStatus.WAITING,
                or_(
                    Token.priority > token.priority,
                    and_(
                        Token.priority == token.priority,
                        Token.created_at < token.created_at,
                    ),
                ),
            )
        )
        result = await session.execute(stmt)
        ahead_count = result.scalar() or 0
        position = ahead_count + 1
        return (position, ahead_count)

    @classmethod
    async def get_waiting_tokens(
        cls,
        session: AsyncSession,
        service_category_id: Optional[uuid.UUID] = None,
        session_id: str = "default",
    ) -> List[Token]:
        """
        Get all waiting tokens ordered by priority DESC, created_at ASC.
        """
        conditions = [
            Token.status == TokenStatus.WAITING,
            Token.session_id == session_id,
        ]
        if service_category_id:
            conditions.append(Token.service_category_id == service_category_id)

        stmt = (
            select(Token)
            .where(and_(*conditions))
            .order_by(Token.priority.desc(), Token.created_at.asc())
            .options(selectinload(Token.service_category))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def validate_transition(cls, current: TokenStatus, target: TokenStatus) -> None:
        """Validate state machine transition invariants."""
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransitionError(current, target)

    @classmethod
    async def call_next_token(
        cls,
        session: AsyncSession,
        counter_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        session_id: str = "default",
    ) -> Optional[Token]:
        """
        Find and call the next waiting token for a counter.
        Enforces counter availability invariants and state transitions.
        """
        counter = await session.get(
            Counter, counter_id, options=[selectinload(Counter.supported_services)]
        )
        if not counter:
            raise CounterNotFoundError(f"Counter with ID '{counter_id}' not found.")

        # Invariant: Closed or Paused counters cannot call tokens
        if counter.status in (CounterStatus.CLOSED, CounterStatus.PAUSED):
            raise CounterUnavailableError(
                f"Counter '{counter.name}' is {counter.status.value}. Open counter before calling next."
            )

        # Invariant: A counter can only serve one token at a time
        if counter.current_token_id is not None:
            active_token = await session.get(Token, counter.current_token_id)
            if active_token and active_token.status in (TokenStatus.CALLED, TokenStatus.SERVING):
                raise CounterUnavailableError(
                    f"Counter '{counter.name}' is already serving token {active_token.display_number}. "
                    "Complete or skip it before calling the next token."
                )

        # Determine services supported by this counter
        supported_service_ids = [svc.id for svc in counter.supported_services]
        conditions = [
            Token.status == TokenStatus.WAITING,
            Token.session_id == session_id,
        ]
        if supported_service_ids:
            conditions.append(Token.service_category_id.in_(supported_service_ids))

        # Select next token in line
        stmt = (
            select(Token)
            .where(and_(*conditions))
            .order_by(Token.priority.desc(), Token.created_at.asc())
            .limit(1)
            .options(selectinload(Token.service_category))
        )
        result = await session.execute(stmt)
        next_token = result.scalar_one_or_none()

        if not next_token:
            return None

        # Perform transition: WAITING -> CALLED
        return await cls.call_token(
            session=session,
            token_id=next_token.id,
            counter_id=counter.id,
            actor_id=actor_id,
        )

    @classmethod
    async def call_token(
        cls,
        session: AsyncSession,
        token_id: uuid.UUID,
        counter_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Token:
        """Transition token from WAITING to CALLED."""
        token = await session.get(
            Token, token_id, options=[selectinload(Token.service_category)]
        )
        if not token:
            raise TokenNotFoundError(f"Token with ID '{token_id}' not found.")

        counter = await session.get(Counter, counter_id)
        if not counter:
            raise CounterNotFoundError(f"Counter with ID '{counter_id}' not found.")

        if counter.status in (CounterStatus.CLOSED, CounterStatus.PAUSED):
            raise CounterUnavailableError(
                f"Cannot call token to a {counter.status.value} counter."
            )

        # Validate transition
        cls.validate_transition(token.status, TokenStatus.CALLED)

        now = datetime.now(timezone.utc)
        token.status = TokenStatus.CALLED
        token.called_counter_id = counter.id
        token.called_at = now

        counter.current_token_id = token.id
        counter.status = CounterStatus.OPEN_SERVING
        counter.status_changed_at = now

        # Record events
        event = ServiceEvent(
            token_id=token.id,
            counter_id=counter.id,
            actor_id=actor_id,
            event_type=ServiceEventType.TOKEN_CALLED,
            timestamp=now,
            reason=f"Called to {counter.name}",
        )
        session.add(event)

        notification = Notification(
            token_id=token.id,
            type=NotificationType.CALLED,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            title="Your Turn!",
            message=f"Please proceed to {counter.name}.",
            created_at=now,
            sent_at=now,
        )
        session.add(notification)

        await session.commit()
        await session.refresh(token)
        return token

    @classmethod
    async def start_serving(
        cls,
        session: AsyncSession,
        token_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Token:
        """Transition token from CALLED to SERVING."""
        token = await session.get(
            Token, token_id, options=[selectinload(Token.service_category)]
        )
        if not token:
            raise TokenNotFoundError(f"Token with ID '{token_id}' not found.")

        cls.validate_transition(token.status, TokenStatus.SERVING)

        now = datetime.now(timezone.utc)
        token.status = TokenStatus.SERVING
        token.service_started_at = now

        event = ServiceEvent(
            token_id=token.id,
            counter_id=token.called_counter_id,
            actor_id=actor_id,
            event_type=ServiceEventType.TOKEN_SERVING,
            timestamp=now,
            reason="Service commenced",
        )
        session.add(event)

        await session.commit()
        await session.refresh(token)
        return token

    @classmethod
    async def complete_token(
        cls,
        session: AsyncSession,
        token_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Token:
        """Transition token from SERVING to COMPLETED and free the counter."""
        token = await session.get(
            Token, token_id, options=[selectinload(Token.service_category)]
        )
        if not token:
            raise TokenNotFoundError(f"Token with ID '{token_id}' not found.")

        cls.validate_transition(token.status, TokenStatus.COMPLETED)

        now = datetime.now(timezone.utc)
        token.status = TokenStatus.COMPLETED
        token.completed_at = now

        # Free counter
        if token.called_counter_id:
            counter = await session.get(Counter, token.called_counter_id)
            if counter and counter.current_token_id == token.id:
                counter.current_token_id = None
                counter.status = CounterStatus.OPEN_IDLE
                counter.status_changed_at = now

        event = ServiceEvent(
            token_id=token.id,
            counter_id=token.called_counter_id,
            actor_id=actor_id,
            event_type=ServiceEventType.TOKEN_COMPLETED,
            timestamp=now,
            reason="Service finished",
        )
        session.add(event)

        notification = Notification(
            token_id=token.id,
            type=NotificationType.COMPLETED,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            title="Service Completed",
            message=f"Service for token {token.display_number} has concluded.",
            created_at=now,
            sent_at=now,
        )
        session.add(notification)

        await session.commit()
        await session.refresh(token)
        return token

    @classmethod
    async def skip_token(
        cls,
        session: AsyncSession,
        token_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = "No-show",
    ) -> Token:
        """Transition token from CALLED or WAITING to SKIPPED."""
        token = await session.get(
            Token, token_id, options=[selectinload(Token.service_category)]
        )
        if not token:
            raise TokenNotFoundError(f"Token with ID '{token_id}' not found.")

        cls.validate_transition(token.status, TokenStatus.SKIPPED)

        now = datetime.now(timezone.utc)
        token.status = TokenStatus.SKIPPED

        # If token was associated with a counter, release the counter
        if token.called_counter_id:
            counter = await session.get(Counter, token.called_counter_id)
            if counter and counter.current_token_id == token.id:
                counter.current_token_id = None
                counter.status = CounterStatus.OPEN_IDLE
                counter.status_changed_at = now

        event = ServiceEvent(
            token_id=token.id,
            counter_id=token.called_counter_id,
            actor_id=actor_id,
            event_type=ServiceEventType.TOKEN_SKIPPED,
            timestamp=now,
            reason=reason or "Skipped",
        )
        session.add(event)

        notification = Notification(
            token_id=token.id,
            type=NotificationType.SKIPPED,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            title="Token Skipped",
            message=f"Token {token.display_number} was skipped: {reason or 'No-show'}.",
            created_at=now,
            sent_at=now,
        )
        session.add(notification)

        await session.commit()
        await session.refresh(token)
        return token

    @classmethod
    async def recall_token(
        cls,
        session: AsyncSession,
        token_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = "Requeued to waiting",
    ) -> Token:
        """Requeue a CALLED token back to WAITING."""
        token = await session.get(
            Token, token_id, options=[selectinload(Token.service_category)]
        )
        if not token:
            raise TokenNotFoundError(f"Token with ID '{token_id}' not found.")

        cls.validate_transition(token.status, TokenStatus.WAITING)

        now = datetime.now(timezone.utc)
        prev_counter_id = token.called_counter_id

        # Release counter
        if prev_counter_id:
            counter = await session.get(Counter, prev_counter_id)
            if counter and counter.current_token_id == token.id:
                counter.current_token_id = None
                counter.status = CounterStatus.OPEN_IDLE
                counter.status_changed_at = now

        token.status = TokenStatus.WAITING
        token.called_counter_id = None
        token.called_at = None

        event = ServiceEvent(
            token_id=token.id,
            counter_id=prev_counter_id,
            actor_id=actor_id,
            event_type=ServiceEventType.TOKEN_RECALLED,
            timestamp=now,
            reason=reason or "Requeued",
        )
        session.add(event)

        await session.commit()
        await session.refresh(token)
        return token

    @classmethod
    async def cancel_token(
        cls,
        session: AsyncSession,
        public_id: str,
        reason: Optional[str] = "Citizen cancelled",
    ) -> Token:
        """Citizen cancels their own WAITING token."""
        token = await cls.get_token_by_public_id(session, public_id)

        cls.validate_transition(token.status, TokenStatus.CANCELLED)

        now = datetime.now(timezone.utc)
        token.status = TokenStatus.CANCELLED
        token.cancelled_at = now

        event = ServiceEvent(
            token_id=token.id,
            counter_id=None,
            event_type=ServiceEventType.TOKEN_CANCELLED,
            timestamp=now,
            reason=reason or "Citizen cancelled",
        )
        session.add(event)

        await session.commit()
        await session.refresh(token)
        return token
