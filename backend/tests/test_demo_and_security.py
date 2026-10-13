"""
QueueWise AI — Milestone 10: Security, Demo & Delivery Invariants Test Suite

Verifies:
- Demo dataset seeder idempotency and structural integrity
- Security boundaries: Public vs protected endpoints, input sanitization, SQLi resistance
- Queue engine state transition invariants under adversarial conditions
- Read-only safety of AI agent and MCP telemetry tools
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.token import Token, TokenStatus
from app.models.counter import Counter, CounterStatus
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent
from app.services.queue_engine import (
    QueueEngine,
    InvalidStateTransitionError,
    CounterUnavailableError,
)
from app.agents.tools import tool_get_queue_snapshot, tool_get_analytics_summary
from app.mcp.server import MCPServer
from scripts.demo_seed import seed_demo_data


@pytest.mark.anyio
class TestDemoDatasetSeeder:
    """Verifies that the demo seeder runs reliably and idempotently."""

    async def test_demo_seed_execution_and_idempotency(self, db_session: AsyncSession):
        """Executing demo seeder multiple times succeeds without unique constraint errors."""
        # Run demo seeder with the active db_session
        await seed_demo_data(db_session)

        # Check that tokens and events exist
        token_count = await db_session.scalar(
            select(func.count(Token.id)).where(Token.public_id.like("demo-%"))
        )
        assert token_count is not None
        # Should have 12 hist + 2 serv + 8 wait + 1 skip + 1 cancel = 24 demo tokens
        assert token_count >= 20

        # Run a second time to verify idempotency
        await seed_demo_data(db_session)

        token_count_after = await db_session.scalar(
            select(func.count(Token.id)).where(Token.public_id.like("demo-%"))
        )
        # Count should remain steady, not double or error
        assert token_count_after == token_count


@pytest.mark.anyio
class TestSecurityAndDataInvariants:
    """Tests security boundaries, input handling, and invariant enforcement."""

    async def test_sqli_resilience_on_token_lookup(self, client: AsyncClient):
        """Adversarial input with SQL injection fragments safely returns 404, never 500."""
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE tokens; --",
            "1 UNION SELECT null, null, null--",
            "../../../etc/passwd",
            "<script>alert(1)</script>",
        ]
        for payload in malicious_inputs:
            resp = await client.get(f"/api/v1/tokens/check/{payload}")
            assert resp.status_code in [404, 422], f"Expected safe rejection for {payload}, got {resp.status_code}"

    async def test_invalid_state_transition_adversarial(self, db_session: AsyncSession):
        """Tokens in terminal states (COMPLETED, CANCELLED) cannot transition backwards."""
        # Retrieve service
        svc_res = await db_session.execute(select(ServiceCategory))
        svc = svc_res.scalars().first()
        assert svc is not None

        # Create token and advance to COMPLETED
        token = await QueueEngine.create_token(
            db_session,
            service_category_id=svc.id,
            session_id="sec_test",
        )
        counters_res = await db_session.execute(select(Counter))
        counter = counters_res.scalars().first()
        assert counter is not None
        counter.status = CounterStatus.OPEN_IDLE
        await db_session.flush()

        token = await QueueEngine.call_token(db_session, token.id, counter.id)
        token = await QueueEngine.start_serving(db_session, token.id, counter.id)
        token = await QueueEngine.complete_token(db_session, token.id, counter.id)
        assert token.status == TokenStatus.COMPLETED

        # Attempt to call completed token must raise InvalidStateTransitionError
        with pytest.raises(InvalidStateTransitionError, match="Illegal transition"):
            await QueueEngine.call_token(db_session, token.id, counter.id)

        # Attempt to cancel completed token must raise InvalidStateTransitionError
        with pytest.raises(InvalidStateTransitionError, match="Illegal transition"):
            await QueueEngine.cancel_token(db_session, token.public_id)

    async def test_closed_counter_cannot_serve(self, db_session: AsyncSession):
        """A closed counter cannot perform operations or call tokens."""
        counters_res = await db_session.execute(select(Counter))
        counter = counters_res.scalars().first()
        assert counter is not None

        # Close counter directly
        counter.status = CounterStatus.CLOSED
        await db_session.flush()

        # Attempting to call next token on closed counter must fail
        with pytest.raises(CounterUnavailableError, match="CLOSED"):
            await QueueEngine.call_next_token(db_session, counter.id, session_id="sec_test")

    async def test_ai_agent_and_mcp_tools_are_read_only(self, db_session: AsyncSession):
        """Executing agent tools leaves database counts unchanged."""
        # Measure initial state
        initial_token_count = await db_session.scalar(select(func.count(Token.id)))
        initial_event_count = await db_session.scalar(select(func.count(ServiceEvent.id)))

        # Invoke all telemetry tools
        await tool_get_queue_snapshot(db_session, "sec_test")
        await tool_get_analytics_summary(db_session, hours_back=24)
        await MCPServer.invoke_tool(db_session, "get_queue_status", {"session_id": "sec_test"})
        await MCPServer.invoke_tool(db_session, "get_analytics_summary", {"session_id": "sec_test"})

        # Assert zero mutations occurred
        final_token_count = await db_session.scalar(select(func.count(Token.id)))
        final_event_count = await db_session.scalar(select(func.count(ServiceEvent.id)))

        assert final_token_count == initial_token_count
        assert final_event_count == initial_event_count
