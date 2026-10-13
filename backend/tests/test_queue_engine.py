"""
QueueWise AI — Queue Engine Unit and Invariant Tests

Tests token issuance, idempotency, queue ordering, state machine transitions,
and invariant enforcement per PRD Section 8.
"""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TokenStatus, CounterStatus, ServiceEventType
from app.models.token import Token
from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent
from app.models.notification import Notification
from app.services.queue_engine import (
    QueueEngine,
    InvalidStateTransitionError,
    CounterUnavailableError,
    TokenNotFoundError,
    ServiceCategoryNotFoundError,
)


@pytest.mark.anyio
async def test_create_token_success(db_session: AsyncSession):
    """Token should be created with unique public_id and sequential display number."""
    token = await QueueEngine.create_token(
        session=db_session,
        service_code="GEN",
        session_id="session-1",
    )
    assert token.id is not None
    assert token.public_id is not None
    assert len(token.public_id) >= 16
    assert token.display_number == "GEN-001"
    assert token.status == TokenStatus.WAITING

    # Create a second token in same category
    token2 = await QueueEngine.create_token(
        session=db_session,
        service_code="GEN",
        session_id="session-1",
    )
    assert token2.public_id != token.public_id
    assert token2.display_number == "GEN-002"

    # Verify ServiceEvent was recorded
    stmt = select(ServiceEvent).where(ServiceEvent.token_id == token.id)
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == ServiceEventType.TOKEN_CREATED

    # Verify Notification was created
    stmt_notif = select(Notification).where(Notification.token_id == token.id)
    notifs = (await db_session.execute(stmt_notif)).scalars().all()
    assert len(notifs) == 1
    assert "GEN-001" in notifs[0].message


@pytest.mark.anyio
async def test_idempotency_duplicate_request_protection(db_session: AsyncSession):
    """Submitting with identical idempotency_key must return original token without creating duplicate."""
    idempotency_key = "client-req-uuid-12345"

    token1 = await QueueEngine.create_token(
        session=db_session,
        service_code="GEN",
        session_id="session-1",
        idempotency_key=idempotency_key,
    )

    token2 = await QueueEngine.create_token(
        session=db_session,
        service_code="GEN",
        session_id="session-1",
        idempotency_key=idempotency_key,
    )

    # Identical token returned
    assert token1.id == token2.id
    assert token1.public_id == token2.public_id
    assert token1.display_number == token2.display_number

    # Only 1 token in DB
    count_stmt = select(func.count(Token.id)).where(Token.session_id == "session-1")
    count = (await db_session.execute(count_stmt)).scalar()
    assert count == 1


@pytest.mark.anyio
async def test_create_token_invalid_service(db_session: AsyncSession):
    """Requesting non-existent service code should raise ServiceCategoryNotFoundError."""
    with pytest.raises(ServiceCategoryNotFoundError):
        await QueueEngine.create_token(
            session=db_session,
            service_code="NONEXISTENT",
        )


@pytest.mark.anyio
async def test_queue_ordering_and_position(db_session: AsyncSession):
    """Queue ordering should follow priority DESC, created_at ASC."""
    session_id = "ordering-test"

    # t1: normal priority 0
    t1 = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id=session_id, priority=0
    )
    # t2: normal priority 0
    t2 = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id=session_id, priority=0
    )
    # t3: high priority 5
    t3 = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id=session_id, priority=5
    )

    # In waiting queue: t3 should be first (high priority), followed by t1, then t2
    waiting = await QueueEngine.get_waiting_tokens(
        session=db_session, session_id=session_id
    )
    assert [t.id for t in waiting] == [t3.id, t1.id, t2.id]

    # Check position calculations
    pos_t3, ahead_t3 = await QueueEngine.get_queue_position_and_ahead(db_session, t3)
    assert pos_t3 == 1
    assert ahead_t3 == 0

    pos_t1, ahead_t1 = await QueueEngine.get_queue_position_and_ahead(db_session, t1)
    assert pos_t1 == 2
    assert ahead_t1 == 1

    pos_t2, ahead_t2 = await QueueEngine.get_queue_position_and_ahead(db_session, t2)
    assert pos_t2 == 3
    assert ahead_t2 == 2


@pytest.mark.anyio
async def test_token_lifecycle_full_flow(db_session: AsyncSession):
    """Test full happy path: WAITING -> CALLED -> SERVING -> COMPLETED."""
    session_id = "lifecycle-test"

    token = await QueueEngine.create_token(
        session=db_session, service_code="DOC", session_id=session_id
    )
    assert token.status == TokenStatus.WAITING

    # Find an open counter
    counter_stmt = select(Counter).where(Counter.status == CounterStatus.OPEN_IDLE).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()

    # 1. Call next token
    called_token = await QueueEngine.call_next_token(
        session=db_session,
        counter_id=counter.id,
        session_id=session_id,
    )
    assert called_token is not None
    assert called_token.id == token.id
    assert called_token.status == TokenStatus.CALLED
    assert called_token.called_counter_id == counter.id
    assert called_token.called_at is not None

    # Check counter state
    await db_session.refresh(counter)
    assert counter.status == CounterStatus.OPEN_SERVING
    assert counter.current_token_id == token.id

    # 2. Start serving
    serving_token = await QueueEngine.start_serving(db_session, token_id=token.id)
    assert serving_token.status == TokenStatus.SERVING
    assert serving_token.service_started_at is not None

    # 3. Complete token
    completed_token = await QueueEngine.complete_token(db_session, token_id=token.id)
    assert completed_token.status == TokenStatus.COMPLETED
    assert completed_token.completed_at is not None

    # Counter should now be released to OPEN_IDLE
    await db_session.refresh(counter)
    assert counter.status == CounterStatus.OPEN_IDLE
    assert counter.current_token_id is None

    # Verify audit events for all steps
    stmt_events = select(ServiceEvent).where(ServiceEvent.token_id == token.id).order_by(ServiceEvent.timestamp.asc())
    events = (await db_session.execute(stmt_events)).scalars().all()
    event_types = [e.event_type for e in events]
    assert event_types == [
        ServiceEventType.TOKEN_CREATED,
        ServiceEventType.TOKEN_CALLED,
        ServiceEventType.TOKEN_SERVING,
        ServiceEventType.TOKEN_COMPLETED,
    ]


@pytest.mark.anyio
async def test_token_skip_flow(db_session: AsyncSession):
    """CALLED token skipped due to no-show releases counter and sets status SKIPPED."""
    token = await QueueEngine.create_token(
        session=db_session, service_code="CASH", session_id="skip-test"
    )

    counter_stmt = select(Counter).where(Counter.status == CounterStatus.OPEN_IDLE).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()

    await QueueEngine.call_token(db_session, token_id=token.id, counter_id=counter.id)
    skipped_token = await QueueEngine.skip_token(db_session, token_id=token.id, reason="No-show after 3 calls")

    assert skipped_token.status == TokenStatus.SKIPPED
    await db_session.refresh(counter)
    assert counter.status == CounterStatus.OPEN_IDLE
    assert counter.current_token_id is None


@pytest.mark.anyio
async def test_token_recall_flow(db_session: AsyncSession):
    """CALLED token can be recalled back to WAITING."""
    token = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id="recall-test"
    )

    counter_stmt = select(Counter).where(Counter.status == CounterStatus.OPEN_IDLE).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()

    await QueueEngine.call_token(db_session, token_id=token.id, counter_id=counter.id)
    recalled_token = await QueueEngine.recall_token(db_session, token_id=token.id, reason="Citizen stepped away")

    assert recalled_token.status == TokenStatus.WAITING
    assert recalled_token.called_counter_id is None
    assert recalled_token.called_at is None
    await db_session.refresh(counter)
    assert counter.status == CounterStatus.OPEN_IDLE
    assert counter.current_token_id is None


@pytest.mark.anyio
async def test_token_cancel_flow(db_session: AsyncSession):
    """Citizen can cancel their WAITING token."""
    token = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id="cancel-test"
    )
    cancelled_token = await QueueEngine.cancel_token(
        db_session, public_id=token.public_id, reason="Changed mind"
    )
    assert cancelled_token.status == TokenStatus.CANCELLED
    assert cancelled_token.cancelled_at is not None


@pytest.mark.anyio
async def test_invariants_closed_counter_cannot_call(db_session: AsyncSession):
    """Invariant: A closed counter cannot call tokens."""
    token = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id="inv-test"
    )

    # Find closed counter
    counter_stmt = select(Counter).where(Counter.status == CounterStatus.CLOSED).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()

    with pytest.raises(CounterUnavailableError):
        await QueueEngine.call_token(db_session, token_id=token.id, counter_id=counter.id)

    with pytest.raises(CounterUnavailableError):
        await QueueEngine.call_next_token(db_session, counter_id=counter.id, session_id="inv-test")


@pytest.mark.anyio
async def test_invariants_cannot_call_next_while_serving(db_session: AsyncSession):
    """Invariant: Counter cannot call next token if already serving without completing."""
    t1 = await QueueEngine.create_token(session=db_session, service_code="GEN", session_id="busy-test")
    t2 = await QueueEngine.create_token(session=db_session, service_code="GEN", session_id="busy-test")

    counter_stmt = select(Counter).where(Counter.status == CounterStatus.OPEN_IDLE).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()

    await QueueEngine.call_next_token(db_session, counter_id=counter.id, session_id="busy-test")

    # Attempting to call next again on same counter while t1 is CALLED must fail
    with pytest.raises(CounterUnavailableError):
        await QueueEngine.call_next_token(db_session, counter_id=counter.id, session_id="busy-test")


@pytest.mark.anyio
async def test_invariants_illegal_transitions_rejected(db_session: AsyncSession):
    """Invariant: Illegal state transitions must be rejected."""
    token = await QueueEngine.create_token(
        session=db_session, service_code="GEN", session_id="illegal-test"
    )

    # Cannot transition directly from WAITING to SERVING or COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        await QueueEngine.start_serving(db_session, token_id=token.id)

    with pytest.raises(InvalidStateTransitionError):
        await QueueEngine.complete_token(db_session, token_id=token.id)

    # Complete the token normally
    counter_stmt = select(Counter).where(Counter.status == CounterStatus.OPEN_IDLE).limit(1)
    counter = (await db_session.execute(counter_stmt)).scalar_one()
    await QueueEngine.call_token(db_session, token_id=token.id, counter_id=counter.id)
    await QueueEngine.start_serving(db_session, token_id=token.id)
    completed_token = await QueueEngine.complete_token(db_session, token_id=token.id)

    # Invariant: A completed token cannot return to WAITING or be transitioned further
    with pytest.raises(InvalidStateTransitionError):
        await QueueEngine.call_token(db_session, token_id=completed_token.id, counter_id=counter.id)

    with pytest.raises(InvalidStateTransitionError):
        await QueueEngine.cancel_token(db_session, public_id=completed_token.public_id)
