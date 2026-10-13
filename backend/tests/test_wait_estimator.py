"""
QueueWise AI — Wait Time Estimator and Dynamic Counters Test Suite

Validates Milestone 3 deliverables:
1. Dynamic wait-time calculations based on queue depth and active counters.
2. Exit condition: "Estimates change when counters change".
3. Stalled queue detection when active counters reach zero.
4. Historical rolling average service duration vs default fallback.
5. Operational queue summary endpoint (GET /api/v1/queues/summary).
6. Prospective arrival wait estimates (GET /api/v1/queues/{service_id}/estimate).
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.counter import Counter
from app.models.token import Token
from app.models.service_category import ServiceCategory
from app.models.enums import CounterStatus, TokenStatus
from app.services.wait_estimator import WaitEstimator


@pytest.mark.anyio
async def test_dynamic_wait_estimate_formula(client: AsyncClient, db_session: AsyncSession):
    """
    Test dynamic wait estimate formula:
    Estimated Wait = ((ahead_count + 1) * Avg Duration) / Active Counters
    """
    # Look up GEN service (default_duration_seconds = 180)
    svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "GEN")
    svc_res = await db_session.execute(svc_stmt)
    gen_svc = svc_res.scalar_one()

    # In seed data: Counter 1 and Counter 2 are OPEN_IDLE, Counter 3 is CLOSED.
    # Active counters = 2.
    active_counters = await WaitEstimator.get_active_counters_for_service(db_session, gen_svc.id)
    assert len(active_counters) == 2

    # Issue token 1 (ahead_count = 0)
    t1_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "test-formula"},
    )
    assert t1_res.status_code == 201
    t1 = t1_res.json()
    assert t1["position_ahead"] == 0
    assert t1["active_counters"] == 2
    # ((0 + 1) * 180) / 2 = 90
    assert t1["estimated_wait_seconds"] == 90

    # Issue token 2 (ahead_count = 1)
    t2_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "test-formula"},
    )
    assert t2_res.status_code == 201
    t2 = t2_res.json()
    assert t2["position_ahead"] == 1
    assert t2["active_counters"] == 2
    # ((1 + 1) * 180) / 2 = 180
    assert t2["estimated_wait_seconds"] == 180

    # Issue token 3 (ahead_count = 2)
    t3_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "test-formula"},
    )
    assert t3_res.status_code == 201
    t3 = t3_res.json()
    assert t3["position_ahead"] == 2
    assert t3["active_counters"] == 2
    # ((2 + 1) * 180) / 2 = 270
    assert t3["estimated_wait_seconds"] == 270


@pytest.mark.anyio
async def test_exit_condition_estimates_change_when_counters_change(
    client: AsyncClient, db_session: AsyncSession
):
    """
    CRITICAL EXIT CONDITION TEST FOR MILESTONE 3:
    'Estimates change when counters change'

    1. Starts with 2 active counters -> token estimate is X.
    2. Opens 3rd counter -> token estimate drops to 2/3 of X.
    3. Closes 2 counters (1 active) -> token estimate triples.
    4. Closes all counters (0 active) -> queue marked STALLED.
    5. Reopens counter -> queue unstalled, estimate resumes.
    """
    # Issue a token in a clean session
    token_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "m3-exit-cond"},
    )
    assert token_res.status_code == 201
    token_data = token_res.json()
    public_id = token_data["public_id"]

    # Initial state with 2 active counters: estimate = (1 * 180) / 2 = 90s
    assert token_data["active_counters"] == 2
    assert token_data["estimated_wait_seconds"] == 90
    assert token_data["is_stalled"] is False

    # Get list of counters
    counters_res = await client.get("/api/v1/counters")
    counters = counters_res.json()
    counter_3 = next(c for c in counters if c["name"] == "Counter 3")
    counter_1 = next(c for c in counters if c["name"] == "Counter 1")
    counter_2 = next(c for c in counters if c["name"] == "Counter 2")

    assert counter_3["status"] == "CLOSED"

    # ACTION 1: Open Counter 3 -> now 3 active counters!
    open_c3_res = await client.post(f"/api/v1/counters/{counter_3['id']}/open")
    assert open_c3_res.status_code == 200
    assert open_c3_res.json()["status"] == "OPEN_IDLE"

    # Check token wait estimate: with 3 counters, (1 * 180) / 3 = 60s!
    track_1 = await client.get(f"/api/v1/tokens/{public_id}")
    assert track_1.status_code == 200
    track_1_data = track_1.json()
    assert track_1_data["active_counters"] == 3
    assert track_1_data["estimated_wait_seconds"] == 60
    assert track_1_data["estimated_wait_seconds"] < token_data["estimated_wait_seconds"]

    # ACTION 2: Close Counter 2 and Counter 3 -> only Counter 1 remains active (1 counter)!
    await client.post(f"/api/v1/counters/{counter_2['id']}/close")
    await client.post(f"/api/v1/counters/{counter_3['id']}/close")

    # Check token wait estimate: with 1 counter, (1 * 180) / 1 = 180s!
    track_2 = await client.get(f"/api/v1/tokens/{public_id}")
    track_2_data = track_2.json()
    assert track_2_data["active_counters"] == 1
    assert track_2_data["estimated_wait_seconds"] == 180
    assert track_2_data["is_stalled"] is False

    # ACTION 3: Close Counter 1 -> 0 active counters! Queue STALLED!
    await client.post(f"/api/v1/counters/{counter_1['id']}/close")

    track_3 = await client.get(f"/api/v1/tokens/{public_id}")
    track_3_data = track_3.json()
    assert track_3_data["active_counters"] == 0
    assert track_3_data["is_stalled"] is True
    # In stalled state, wait estimate assumes single-counter baseline when resumed
    assert track_3_data["estimated_wait_seconds"] == 180

    # ACTION 4: Reopen Counter 1 and Counter 2
    await client.post(f"/api/v1/counters/{counter_1['id']}/open")
    await client.post(f"/api/v1/counters/{counter_2['id']}/open")

    track_4 = await client.get(f"/api/v1/tokens/{public_id}")
    track_4_data = track_4.json()
    assert track_4_data["active_counters"] == 2
    assert track_4_data["is_stalled"] is False
    assert track_4_data["estimated_wait_seconds"] == 90


@pytest.mark.anyio
async def test_historical_rolling_average_duration(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test that when completed tokens have service duration history,
    WaitEstimator computes the average duration from real events instead of default.
    """
    svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "DOC")
    svc_res = await db_session.execute(svc_stmt)
    doc_svc = svc_res.scalar_one()

    # Seed 3 completed tokens with actual recorded durations of 120s each
    # (Default for DOC is 360s, so 120s is notably faster)
    now = datetime.now(timezone.utc)
    for i in range(3):
        completed_token = Token(
            public_id=f"doc-hist-{i}",
            display_number=f"DOC-99{i}",
            service_category_id=doc_svc.id,
            session_id="hist-test",
            status=TokenStatus.COMPLETED,
            created_at=now - timedelta(minutes=10),
            called_at=now - timedelta(minutes=5),
            service_started_at=now - timedelta(seconds=120),
            completed_at=now,
        )
        db_session.add(completed_token)
    await db_session.commit()

    # Check average service duration
    avg_sec, basis, confidence = await WaitEstimator.get_average_service_duration(
        db_session, doc_svc.id
    )
    assert basis == "HISTORICAL_WINDOW"
    assert avg_sec == 120  # Computed from actual completed tokens!
    assert confidence in ("MEDIUM", "HIGH")


@pytest.mark.anyio
async def test_queue_summary_metrics_endpoint(client: AsyncClient):
    """GET /api/v1/queues/summary returns system-wide metrics."""
    res = await client.get("/api/v1/queues/summary")
    assert res.status_code == 200
    data = res.json()

    assert "session_id" in data
    assert "timestamp" in data
    assert "total_waiting" in data
    assert "total_serving" in data
    assert "total_active_counters" in data
    assert "services" in data
    assert len(data["services"]) >= 3

    # Check fields in each service summary item
    for item in data["services"]:
        assert "service_id" in item
        assert "service_name" in item
        assert "service_code" in item
        assert "waiting_count" in item
        assert "serving_count" in item
        assert "active_counters" in item
        assert "total_counters" in item
        assert "avg_service_duration_seconds" in item
        assert "estimated_wait_for_next_arrival" in item
        assert "queue_status" in item
        assert item["queue_status"] in ("NORMAL", "BUSY", "CONGESTED", "STALLED")
        assert "currently_serving" in item


@pytest.mark.anyio
async def test_prospective_arrival_estimate_endpoint(client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/queues/{service_id}/estimate returns prospective arrival estimate."""
    svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "CASH")
    svc_res = await db_session.execute(svc_stmt)
    cash_svc = svc_res.scalar_one()

    res = await client.get(f"/api/v1/queues/{cash_svc.id}/estimate")
    assert res.status_code == 200
    data = res.json()

    assert data["service_id"] == str(cash_svc.id)
    assert data["service_code"] == "CASH"
    assert "position_ahead" in data
    assert "active_counters" in data
    assert "estimated_wait_seconds" in data
    assert "status_message" in data
    assert data["avg_service_duration_seconds"] == cash_svc.default_duration_seconds
