"""
QueueWise AI — Counter Operations Test Suite

Validates Milestone 3 counter management and operator actions:
1. Counter status lifecycle: OPEN_IDLE -> PAUSED -> RESUME -> CLOSED.
2. Invariants: cannot close or pause while serving an active token.
3. Operator assignment (assign/unassign).
4. Supported service categories configuration.
5. Service events and audit logging on counter operations.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent
from app.models.enums import CounterStatus, ServiceEventType


@pytest.mark.anyio
async def test_counter_lifecycle_open_pause_resume_close(client: AsyncClient):
    """Test standard counter operator state transitions."""
    # List counters to get a CLOSED counter
    counters_res = await client.get("/api/v1/counters")
    assert counters_res.status_code == 200
    counters = counters_res.json()
    counter = next(c for c in counters if c["status"] == "CLOSED")
    c_id = counter["id"]

    # 1. OPEN counter -> OPEN_IDLE
    open_res = await client.post(f"/api/v1/counters/{c_id}/open")
    assert open_res.status_code == 200
    assert open_res.json()["status"] == "OPEN_IDLE"

    # 2. PAUSE counter -> PAUSED
    pause_res = await client.post(f"/api/v1/counters/{c_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # 3. RESUME counter -> OPEN_IDLE
    resume_res = await client.post(f"/api/v1/counters/{c_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "OPEN_IDLE"

    # 4. CLOSE counter -> CLOSED
    close_res = await client.post(f"/api/v1/counters/{c_id}/close")
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"


@pytest.mark.anyio
async def test_counter_cannot_pause_or_close_while_serving(client: AsyncClient):
    """
    INVARIANT TEST:
    A counter cannot be PAUSED or CLOSED while actively serving a token.
    Must first complete or skip the token.
    """
    # Create token
    tok_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "invariant-test"},
    )
    assert tok_res.status_code == 201

    # Get an open counter
    counters = (await client.get("/api/v1/counters")).json()
    counter = next(c for c in counters if c["status"] == "OPEN_IDLE")
    c_id = counter["id"]

    # Call and start serving token
    call_res = await client.post(f"/api/v1/counters/{c_id}/call-next?session_id=invariant-test")
    assert call_res.status_code == 200

    serve_res = await client.post(f"/api/v1/counters/{c_id}/serve")
    assert serve_res.status_code == 200

    # Attempt to PAUSE while serving -> 409 Conflict
    pause_res = await client.post(f"/api/v1/counters/{c_id}/pause")
    assert pause_res.status_code == 409
    assert "Cannot close or pause counter while serving" in pause_res.json()["detail"]

    # Attempt to CLOSE while serving -> 409 Conflict
    close_res = await client.post(f"/api/v1/counters/{c_id}/close")
    assert close_res.status_code == 409
    assert "Cannot close or pause counter while serving" in close_res.json()["detail"]

    # Complete service -> Counter becomes OPEN_IDLE
    comp_res = await client.post(f"/api/v1/counters/{c_id}/complete")
    assert comp_res.status_code == 200

    # Now counter CAN be paused and closed!
    pause_ok = await client.post(f"/api/v1/counters/{c_id}/pause")
    assert pause_ok.status_code == 200
    assert pause_ok.json()["status"] == "PAUSED"

    close_ok = await client.post(f"/api/v1/counters/{c_id}/close")
    assert close_ok.status_code == 200
    assert close_ok.json()["status"] == "CLOSED"


@pytest.mark.anyio
async def test_counter_services_reconfiguration(client: AsyncClient, db_session: AsyncSession):
    """Test reassigning which services a counter supports."""
    counters = (await client.get("/api/v1/counters")).json()
    c_id = counters[0]["id"]

    # Get DOC service only
    svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "DOC")
    svc_res = await db_session.execute(svc_stmt)
    doc_svc = svc_res.scalar_one()

    # Reconfigure counter to ONLY support DOC
    put_res = await client.put(
        f"/api/v1/counters/{c_id}/services",
        json={"supported_service_ids": [str(doc_svc.id)]},
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert len(updated["supported_services"]) == 1
    assert updated["supported_services"][0]["code"] == "DOC"


@pytest.mark.anyio
async def test_counter_events_logged(client: AsyncClient, db_session: AsyncSession):
    """Verify counter status change events are recorded in ServiceEvent table."""
    counters = (await client.get("/api/v1/counters")).json()
    c_id = counters[0]["id"]

    # Trigger status change
    await client.post(f"/api/v1/counters/{c_id}/open")

    # Check ServiceEvent table
    evt_stmt = select(ServiceEvent).where(
        ServiceEvent.counter_id == uuid.UUID(c_id),
        ServiceEvent.event_type == ServiceEventType.COUNTER_STATUS_CHANGED,
    )
    evt_res = await db_session.execute(evt_stmt)
    events = evt_res.scalars().all()
    assert len(events) >= 1
    assert "Status changed" in events[-1].reason
