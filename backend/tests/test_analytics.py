"""
QueueWise AI — Operational Analytics Test Suite

Verifies:
  1. Accurate metric calculations directly from stored Token and ServiceEvent records
  2. Exit condition: "Dashboard values from stored events"
  3. Calculation of throughput, wait times, service durations, and SLA compliance
  4. Hourly distribution and per-service/counter aggregations
  5. Analytics REST API endpoints (/summary, /hourly, /services, /counters, /events, /dashboard)
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.token import Token
from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent
from app.models.enums import TokenStatus, CounterStatus, ServiceEventType
from app.services.analytics_service import AnalyticsService
from app.services.queue_engine import QueueEngine


class TestOperationalAnalyticsCalculations:
    """Verifies that metric calculations match known database records."""

    @pytest.mark.anyio
    async def test_summary_metrics_calculated_from_known_tokens(
        self, db_session: AsyncSession
    ):
        """
        Create 5 tokens with known lifecycle states and verify accurate metric aggregation.
        """
        # Fetch seeded service and counter
        svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "GEN")
        svc_res = await db_session.execute(svc_stmt)
        svc = svc_res.scalar_one()

        c_stmt = select(Counter).limit(1)
        c_res = await db_session.execute(c_stmt)
        counter = c_res.scalar_one()

        base_time = datetime.now(timezone.utc) - timedelta(hours=2)

        # 1. Completed Token (wait: 120s, service: 180s)
        t1 = Token(
            public_id="token_test_1",
            display_number="GEN-101",
            service_category_id=svc.id,
            session_id="analytics_test",
            status=TokenStatus.COMPLETED,
            created_at=base_time,
            called_at=base_time + timedelta(seconds=120),
            service_started_at=base_time + timedelta(seconds=120),
            completed_at=base_time + timedelta(seconds=300),
            called_counter_id=counter.id,
        )

        # 2. Completed Token (wait: 240s, service: 300s)
        t2 = Token(
            public_id="token_test_2",
            display_number="GEN-102",
            service_category_id=svc.id,
            session_id="analytics_test",
            status=TokenStatus.COMPLETED,
            created_at=base_time,
            called_at=base_time + timedelta(seconds=240),
            service_started_at=base_time + timedelta(seconds=240),
            completed_at=base_time + timedelta(seconds=540),
            called_counter_id=counter.id,
        )

        # 3. Skipped Token (no-show)
        t3 = Token(
            public_id="token_test_3",
            display_number="GEN-103",
            service_category_id=svc.id,
            session_id="analytics_test",
            status=TokenStatus.SKIPPED,
            created_at=base_time,
            called_at=base_time + timedelta(seconds=60),
        )

        # 4. Cancelled Token
        t4 = Token(
            public_id="token_test_4",
            display_number="GEN-104",
            service_category_id=svc.id,
            session_id="analytics_test",
            status=TokenStatus.CANCELLED,
            created_at=base_time,
            cancelled_at=base_time + timedelta(seconds=30),
        )

        # 5. Waiting Token
        t5 = Token(
            public_id="token_test_5",
            display_number="GEN-105",
            service_category_id=svc.id,
            session_id="analytics_test",
            status=TokenStatus.WAITING,
            created_at=base_time,
        )

        db_session.add_all([t1, t2, t3, t4, t5])
        await db_session.commit()

        # Compute summary metrics scoped to this test session
        summary = await AnalyticsService.get_summary_metrics(
            session=db_session,
            session_id="analytics_test",
            target_sla_seconds=600,
        )

        assert summary.total_tokens_issued == 5
        assert summary.tokens_completed == 2
        assert summary.tokens_skipped == 1
        assert summary.tokens_cancelled == 1
        assert summary.tokens_currently_waiting == 1

        # Completed rates: 2/5 = 40.0%
        assert summary.completion_rate_pct == 40.0
        assert summary.no_show_rate_pct == 20.0
        assert summary.cancellation_rate_pct == 20.0

        # Wait times: t1 (120s), t2 (240s), t3 (60s) -> average = (120+240+60)/3 = 140s
        assert summary.avg_wait_seconds == 140
        assert summary.max_wait_seconds == 240

        # Service durations: t1 (180s), t2 (300s) -> average = (180+300)/2 = 240s
        assert summary.avg_service_seconds == 240

        # SLA compliance: all 3 called tokens waited <= 600s -> 0 breaches, 100% compliance
        assert summary.sla_breach_count == 0
        assert summary.sla_compliance_pct == 100.0

    @pytest.mark.anyio
    async def test_sla_breach_detection(self, db_session: AsyncSession):
        """
        Tokens with wait times exceeding the SLA threshold are accurately flagged.
        """
        svc_stmt = select(ServiceCategory).limit(1)
        svc_res = await db_session.execute(svc_stmt)
        svc = svc_res.scalar_one()

        now = datetime.now(timezone.utc)
        # Token that waited 900 seconds (15 minutes, exceeding 10m / 600s SLA)
        breached_token = Token(
            public_id="token_breach_1",
            display_number="SLA-001",
            service_category_id=svc.id,
            session_id="sla_test",
            status=TokenStatus.COMPLETED,
            created_at=now - timedelta(seconds=1200),
            called_at=now - timedelta(seconds=300),  # wait = 900s
            service_started_at=now - timedelta(seconds=300),
            completed_at=now,
        )
        db_session.add(breached_token)
        await db_session.commit()

        summary = await AnalyticsService.get_summary_metrics(
            session=db_session,
            session_id="sla_test",
            target_sla_seconds=600,
        )

        assert summary.sla_breach_count == 1
        assert summary.sla_compliance_pct == 0.0  # 1 out of 1 breached


class TestExitConditionDashboardValuesFromStoredEvents:
    """
    Mandatory challenge exit condition:
    'Dashboard values from stored events'
    """

    @pytest.mark.anyio
    async def test_exit_condition_metrics_derive_from_real_events(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Execute real queue transactions (create -> call -> serve -> complete)
        and verify that the analytics API returns metrics computed from those events.
        """
        # 1. Create token via API
        create_resp = await client.post(
            "/api/v1/tokens",
            json={"service_code": "GEN", "session_id": "real_events_session"},
        )
        assert create_resp.status_code == 201
        token_data = create_resp.json()
        public_id = token_data["public_id"]
        token_num = token_data["display_number"]

        # Fetch open counter
        c_resp = await client.get("/api/v1/counters")
        assert c_resp.status_code == 200
        counters = c_resp.json()
        counter_id = counters[0]["id"]

        # Ensure counter is open
        await client.patch(f"/api/v1/counters/{counter_id}/status", json={"status": "OPEN_IDLE"})

        # 2. Call token
        call_resp = await client.post(
            f"/api/v1/counters/{counter_id}/call-next?session_id=real_events_session"
        )
        assert call_resp.status_code == 200

        # 3. Serve token
        serve_resp = await client.post(f"/api/v1/counters/{counter_id}/serve")
        assert serve_resp.status_code == 200

        # 4. Complete token
        comp_resp = await client.post(f"/api/v1/counters/{counter_id}/complete")
        assert comp_resp.status_code == 200

        # 5. Query analytics dashboard API
        dash_resp = await client.get("/api/v1/analytics/dashboard?session_id=real_events_session")
        assert dash_resp.status_code == 200
        data = dash_resp.json()

        # Verify summary reflects the real completed token
        summary = data["summary"]
        assert summary["total_tokens_issued"] >= 1
        assert summary["tokens_completed"] >= 1

        # Verify recent events log contains the real ServiceEvent records
        events = data["recent_events"]
        assert len(events) > 0
        event_types = [e["event_type"] for e in events]
        assert "TOKEN_CREATED" in event_types
        assert "TOKEN_CALLED" in event_types
        assert "TOKEN_COMPLETED" in event_types

        # Verify token display number appears in event log
        event_token_numbers = [e["token_display_number"] for e in events if e["token_display_number"]]
        assert token_num in event_token_numbers


class TestAnalyticsAPIEndpoints:
    """Integration tests for all /api/v1/analytics/* endpoints."""

    @pytest.mark.anyio
    async def test_get_summary_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/summary returns 200 with summary KPIs."""
        resp = await client.get("/api/v1/analytics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tokens_issued" in data
        assert "tokens_completed" in data
        assert "avg_wait_seconds" in data
        assert "sla_compliance_pct" in data

    @pytest.mark.anyio
    async def test_get_hourly_trends_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/hourly returns 24 hourly buckets."""
        resp = await client.get("/api/v1/analytics/hourly")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 24
        assert data[0]["hour"] == 0
        assert data[23]["hour"] == 23

    @pytest.mark.anyio
    async def test_get_services_performance_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/services returns breakdown for all categories."""
        resp = await client.get("/api/v1/analytics/services")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        codes = [s["service_code"] for s in data]
        assert "GEN" in codes

    @pytest.mark.anyio
    async def test_get_counters_performance_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/counters returns breakdown for physical desks."""
        resp = await client.get("/api/v1/analytics/counters")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "counter_name" in data[0]
        assert "utilization_pct" in data[0]

    @pytest.mark.anyio
    async def test_get_events_feed_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/events returns recent ServiceEvent records."""
        resp = await client.get("/api/v1/analytics/events?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_dashboard_endpoint(self, client: AsyncClient):
        """GET /api/v1/analytics/dashboard returns unified payload."""
        resp = await client.get("/api/v1/analytics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "hourly_trends" in data
        assert "services" in data
        assert "counters" in data
        assert "recent_events" in data
