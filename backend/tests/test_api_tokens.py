"""
QueueWise AI — Token and Counter API Integration Tests

Tests REST API endpoints for token issuance, status tracking, cancellation,
services listing, and counter operator workflows.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_services(client: AsyncClient):
    """GET /api/v1/services returns list of seeded service categories."""
    response = await client.get("/api/v1/services")
    assert response.status_code == 200
    services = response.json()
    assert len(services) >= 3
    codes = [s["code"] for s in services]
    assert "GEN" in codes
    assert "DOC" in codes
    assert "CASH" in codes


@pytest.mark.anyio
async def test_create_service(client: AsyncClient):
    """POST /api/v1/services creates a new service category."""
    payload = {
        "name": "Pharmacy Dispensation",
        "code": "PHARM",
        "description": "Prescription fulfillment and consultation",
        "default_duration_seconds": 200,
        "priority_policy": "FIFO",
        "is_active": True,
    }
    response = await client.post("/api/v1/services", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "PHARM"
    assert data["name"] == "Pharmacy Dispensation"
    assert "id" in data


@pytest.mark.anyio
async def test_create_token_and_track_status(client: AsyncClient):
    """POST /api/v1/tokens issues token; GET /api/v1/tokens/{public_id} returns live tracking."""
    # Issue token
    create_payload = {
        "service_code": "GEN",
        "session_id": "api-test",
        "contact_info": "+923001234567",
    }
    create_res = await client.post("/api/v1/tokens", json=create_payload)
    assert create_res.status_code == 201
    token_data = create_res.json()

    assert "public_id" in token_data
    assert token_data["display_number"].startswith("GEN-")
    assert token_data["status"] == "WAITING"
    assert token_data["position_ahead"] == 0
    assert token_data["estimated_wait_seconds"] > 0
    assert token_data["service_name"] == "General Inquiries & Token Issuance"

    public_id = token_data["public_id"]

    # Track status
    get_res = await client.get(f"/api/v1/tokens/{public_id}")
    assert get_res.status_code == 200
    status_data = get_res.json()
    assert status_data["public_id"] == public_id
    assert status_data["status"] == "WAITING"
    assert status_data["display_number"] == token_data["display_number"]


@pytest.mark.anyio
async def test_idempotent_token_creation_via_api(client: AsyncClient):
    """Duplicate POST /api/v1/tokens with same idempotency_key returns identical token."""
    payload = {
        "service_code": "GEN",
        "session_id": "api-idempotency",
        "idempotency_key": "unique-client-key-999",
    }
    res1 = await client.post("/api/v1/tokens", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()

    res2 = await client.post("/api/v1/tokens", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()

    assert data1["public_id"] == data2["public_id"]
    assert data1["display_number"] == data2["display_number"]


@pytest.mark.anyio
async def test_cancel_token_via_api(client: AsyncClient):
    """POST /api/v1/tokens/{public_id}/cancel cancels waiting token."""
    create_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "DOC", "session_id": "cancel-api"},
    )
    assert create_res.status_code == 201
    public_id = create_res.json()["public_id"]

    cancel_res = await client.post(
        f"/api/v1/tokens/{public_id}/cancel",
        params={"reason": "Citizen left the building"},
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "CANCELLED"

    # Cancelling again returns 409
    cancel_again = await client.post(f"/api/v1/tokens/{public_id}/cancel")
    assert cancel_again.status_code == 409


@pytest.mark.anyio
async def test_counters_operator_workflow_via_api(client: AsyncClient):
    """Complete operator counter workflow: list counters, call-next, serve, complete."""
    # 1. Create a token
    tok_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "operator-api"},
    )
    token_data = tok_res.json()
    public_id = token_data["public_id"]

    # 2. List counters
    counters_res = await client.get("/api/v1/counters")
    assert counters_res.status_code == 200
    counters = counters_res.json()
    idle_counter = next(c for c in counters if c["status"] == "OPEN_IDLE")
    counter_id = idle_counter["id"]

    # 3. Call next token to counter
    call_res = await client.post(
        f"/api/v1/counters/{counter_id}/call-next",
        params={"session_id": "operator-api"},
    )
    assert call_res.status_code == 200
    called = call_res.json()
    assert called["status"] == "CALLED"
    assert called["public_id"] == public_id

    # Citizen tracking shows CALLED and counter name
    track_res = await client.get(f"/api/v1/tokens/{public_id}")
    track_data = track_res.json()
    assert track_data["status"] == "CALLED"
    assert track_data["called_counter_name"] == idle_counter["name"]

    # 4. Operator starts serving
    serve_res = await client.post(f"/api/v1/counters/{counter_id}/serve")
    assert serve_res.status_code == 200
    assert serve_res.json()["status"] == "SERVING"

    # 5. Operator completes service
    comp_res = await client.post(f"/api/v1/counters/{counter_id}/complete")
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

    # Citizen tracking shows COMPLETED
    track_final = await client.get(f"/api/v1/tokens/{public_id}")
    assert track_final.json()["status"] == "COMPLETED"
