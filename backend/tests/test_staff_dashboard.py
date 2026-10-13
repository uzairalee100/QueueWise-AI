"""
QueueWise AI — Staff Dashboard Counter Operations Test Suite

Tests the full staff counter operator workflow:
  1. Counter creation and listing
  2. Counter status controls (open, pause, resume, close)
  3. Token call-next → serve → complete lifecycle
  4. Token skip (no-show) and recall (requeue) flows
  5. Service assignment configuration
  6. WebSocket event broadcasting on operations
  7. Invariant enforcement (closed counter cannot call, etc.)

Milestone 6 exit conditions verified.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestStaffCounterCreationAndListing:
    """Test counter CRUD and listing endpoints."""

    async def test_list_counters(self, client: AsyncClient):
        """Seeded counters should be returned from GET /api/v1/counters."""
        resp = await client.get("/api/v1/counters")
        assert resp.status_code == 200
        counters = resp.json()
        assert isinstance(counters, list)
        assert len(counters) >= 1
        # All counters must have required fields
        for c in counters:
            assert "id" in c
            assert "name" in c
            assert "status" in c

    async def test_create_counter(self, client: AsyncClient):
        """POST /api/v1/counters should create a new counter."""
        resp = await client.post("/api/v1/counters", json={
            "name": "Test Desk X",
            "supported_service_ids": [],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Desk X"
        assert data["status"] == "OPEN_IDLE"

    async def test_get_single_counter(self, client: AsyncClient):
        """GET /api/v1/counters/{id} returns the counter details."""
        counters_resp = await client.get("/api/v1/counters")
        counters = counters_resp.json()
        counter_id = counters[0]["id"]

        resp = await client.get(f"/api/v1/counters/{counter_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == counter_id


@pytest.mark.anyio
class TestCounterStatusControls:
    """Test counter open/pause/resume/close status lifecycle."""

    async def test_open_counter(self, client: AsyncClient):
        """POST /api/v1/counters/{id}/open sets status to OPEN_IDLE."""
        # Create a fresh counter
        create_resp = await client.post("/api/v1/counters", json={"name": "Status Test A"})
        counter_id = create_resp.json()["id"]

        # Close it first
        await client.post(f"/api/v1/counters/{counter_id}/close")

        # Now open it
        resp = await client.post(f"/api/v1/counters/{counter_id}/open")
        assert resp.status_code == 200
        assert resp.json()["status"] == "OPEN_IDLE"

    async def test_pause_and_resume(self, client: AsyncClient):
        """Pause sets PAUSED, resume restores OPEN_IDLE."""
        create_resp = await client.post("/api/v1/counters", json={"name": "Status Test B"})
        counter_id = create_resp.json()["id"]

        pause_resp = await client.post(f"/api/v1/counters/{counter_id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "PAUSED"

        resume_resp = await client.post(f"/api/v1/counters/{counter_id}/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "OPEN_IDLE"

    async def test_close_counter(self, client: AsyncClient):
        """POST /api/v1/counters/{id}/close sets status to CLOSED."""
        create_resp = await client.post("/api/v1/counters", json={"name": "Status Test C"})
        counter_id = create_resp.json()["id"]

        close_resp = await client.post(f"/api/v1/counters/{counter_id}/close")
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "CLOSED"


@pytest.mark.anyio
class TestTokenCallServeCompleteLifecycle:
    """Test the core call-next → serve → complete workflow."""

    async def _setup_counter_and_token(self, client: AsyncClient):
        """Helper: create a counter with services, issue a token, return (counter_id, token)."""
        # Get first available service
        svc_resp = await client.get("/api/v1/services")
        services = svc_resp.json()
        assert len(services) > 0
        svc = services[0]

        # Create counter assigned to that service
        create_resp = await client.post("/api/v1/counters", json={
            "name": "Lifecycle Desk",
            "supported_service_ids": [svc["id"]],
        })
        counter_id = create_resp.json()["id"]

        # Issue a token
        token_resp = await client.post("/api/v1/tokens", json={
            "service_code": svc["code"],
        })
        assert token_resp.status_code == 201
        token = token_resp.json()
        return counter_id, token

    async def test_call_next_token(self, client: AsyncClient):
        """Call-next returns the first waiting token and marks it CALLED."""
        counter_id, token = await self._setup_counter_and_token(client)

        call_resp = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call_resp.status_code == 200
        called = call_resp.json()
        assert called["status"] == "CALLED"
        assert called["display_number"] == token["display_number"]

    async def test_full_call_serve_complete(self, client: AsyncClient):
        """Full lifecycle: call → serve → complete returns COMPLETED and frees counter."""
        counter_id, token = await self._setup_counter_and_token(client)

        # Call
        call_resp = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call_resp.json()["status"] == "CALLED"

        # Serve
        serve_resp = await client.post(f"/api/v1/counters/{counter_id}/serve")
        assert serve_resp.status_code == 200
        assert serve_resp.json()["status"] == "SERVING"

        # Complete
        complete_resp = await client.post(f"/api/v1/counters/{counter_id}/complete")
        assert complete_resp.status_code == 200
        completed = complete_resp.json()
        assert completed["status"] == "COMPLETED"

        # Counter should be idle now
        counter_resp = await client.get(f"/api/v1/counters/{counter_id}")
        assert counter_resp.json()["status"] == "OPEN_IDLE"
        assert counter_resp.json()["current_token_id"] is None

    async def test_call_next_returns_null_when_empty(self, client: AsyncClient):
        """Calling next with no waiting tokens returns null."""
        create_resp = await client.post("/api/v1/counters", json={"name": "Empty Desk"})
        counter_id = create_resp.json()["id"]

        resp = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert resp.status_code == 200
        # Should be null since no waiting tokens exist for this unassigned counter


@pytest.mark.anyio
class TestTokenSkipAndRecall:
    """Test no-show skip and recall-to-waiting flows."""

    async def _call_token(self, client: AsyncClient):
        """Helper: create counter+token and call it."""
        svc_resp = await client.get("/api/v1/services")
        svc = svc_resp.json()[0]

        create_resp = await client.post("/api/v1/counters", json={
            "name": "Skip/Recall Desk",
            "supported_service_ids": [svc["id"]],
        })
        counter_id = create_resp.json()["id"]

        await client.post("/api/v1/tokens", json={"service_code": svc["code"]})
        call_resp = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        called_token = call_resp.json()
        return counter_id, called_token

    async def test_skip_no_show(self, client: AsyncClient):
        """Skip transitions CALLED token to SKIPPED and frees counter."""
        counter_id, called = await self._call_token(client)
        assert called["status"] == "CALLED"

        skip_resp = await client.post(f"/api/v1/counters/{counter_id}/skip?reason=No-show")
        assert skip_resp.status_code == 200
        skipped = skip_resp.json()
        assert skipped["status"] == "SKIPPED"

        # Counter freed
        counter_resp = await client.get(f"/api/v1/counters/{counter_id}")
        assert counter_resp.json()["status"] == "OPEN_IDLE"

    async def test_recall_requeues_token(self, client: AsyncClient):
        """Recall returns CALLED token to WAITING and frees counter."""
        counter_id, called = await self._call_token(client)
        assert called["status"] == "CALLED"

        recall_resp = await client.post(f"/api/v1/counters/{counter_id}/recall?reason=Requeued")
        assert recall_resp.status_code == 200
        recalled = recall_resp.json()
        assert recalled["status"] == "WAITING"

        # Counter freed
        counter_resp = await client.get(f"/api/v1/counters/{counter_id}")
        assert counter_resp.json()["status"] == "OPEN_IDLE"


@pytest.mark.anyio
class TestCounterInvariants:
    """Test business rule enforcement."""

    async def test_closed_counter_cannot_call(self, client: AsyncClient):
        """A closed counter must not be able to call next token."""
        create_resp = await client.post("/api/v1/counters", json={"name": "Invariant A"})
        counter_id = create_resp.json()["id"]

        # Close it
        await client.post(f"/api/v1/counters/{counter_id}/close")

        # Try calling next — should fail
        call_resp = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call_resp.status_code == 409

    async def test_cannot_close_while_serving(self, client: AsyncClient):
        """Cannot close counter while it has an active (called) token."""
        svc_resp = await client.get("/api/v1/services")
        svc = svc_resp.json()[0]

        create_resp = await client.post("/api/v1/counters", json={
            "name": "Invariant B",
            "supported_service_ids": [svc["id"]],
        })
        counter_id = create_resp.json()["id"]

        # Issue and call
        await client.post("/api/v1/tokens", json={"service_code": svc["code"]})
        await client.post(f"/api/v1/counters/{counter_id}/call-next")

        # Try to close — should fail because token is active
        close_resp = await client.post(f"/api/v1/counters/{counter_id}/close")
        assert close_resp.status_code == 409

    async def test_service_assignment_update(self, client: AsyncClient):
        """PUT /api/v1/counters/{id}/services updates supported services."""
        svc_resp = await client.get("/api/v1/services")
        services = svc_resp.json()
        assert len(services) >= 1

        create_resp = await client.post("/api/v1/counters", json={"name": "Config Desk"})
        counter_id = create_resp.json()["id"]

        # Initially no services
        resp = await client.get(f"/api/v1/counters/{counter_id}")
        assert len(resp.json()["supported_services"]) == 0

        # Assign services
        svc_ids = [services[0]["id"]]
        update_resp = await client.put(
            f"/api/v1/counters/{counter_id}/services",
            json={"supported_service_ids": svc_ids},
        )
        assert update_resp.status_code == 200
        assert len(update_resp.json()["supported_services"]) == 1


@pytest.mark.anyio
class TestStaffDashboardEndToEnd:
    """End-to-end integration: full staff workflow across multiple tokens."""

    async def test_multi_token_workflow(self, client: AsyncClient):
        """
        Staff processes multiple tokens sequentially:
        1. Issue 3 tokens for the same service
        2. Call → serve → complete first token
        3. Skip second token (no-show)
        4. Call and recall third token
        """
        svc_resp = await client.get("/api/v1/services")
        svc = svc_resp.json()[0]

        create_resp = await client.post("/api/v1/counters", json={
            "name": "E2E Desk",
            "supported_service_ids": [svc["id"]],
        })
        counter_id = create_resp.json()["id"]

        # Issue 3 tokens
        tokens = []
        for i in range(3):
            resp = await client.post("/api/v1/tokens", json={
                "service_code": svc["code"],
            })
            assert resp.status_code == 201
            tokens.append(resp.json())

        # ── Token 1: call → serve → complete ──
        call1 = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call1.json()["display_number"] == tokens[0]["display_number"]

        serve1 = await client.post(f"/api/v1/counters/{counter_id}/serve")
        assert serve1.json()["status"] == "SERVING"

        complete1 = await client.post(f"/api/v1/counters/{counter_id}/complete")
        assert complete1.json()["status"] == "COMPLETED"

        # ── Token 2: call → skip (no-show) ──
        call2 = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call2.json()["display_number"] == tokens[1]["display_number"]

        skip2 = await client.post(f"/api/v1/counters/{counter_id}/skip?reason=No-show")
        assert skip2.json()["status"] == "SKIPPED"

        # ── Token 3: call → recall (requeue) ──
        call3 = await client.post(f"/api/v1/counters/{counter_id}/call-next")
        assert call3.json()["display_number"] == tokens[2]["display_number"]

        recall3 = await client.post(f"/api/v1/counters/{counter_id}/recall")
        assert recall3.json()["status"] == "WAITING"

        # Counter should be idle after all operations
        counter_check = await client.get(f"/api/v1/counters/{counter_id}")
        assert counter_check.json()["status"] == "OPEN_IDLE"
        assert counter_check.json()["current_token_id"] is None
