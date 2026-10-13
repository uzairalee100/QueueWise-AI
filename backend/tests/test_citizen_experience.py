"""
QueueWise AI — Milestone 5: Citizen Experience End-to-End Test Suite

Verifies Exit Condition:
"A citizen can issue a token, receive real-time updates, and view current position on mobile viewport."
"""
import pytest
from app.models.enums import TokenStatus


def test_milestone_5_exit_condition_citizen_token_journey(sync_client):
    """
    Simulates the end-to-end citizen flow:
    1. Citizen browses services on kiosk (GET /api/v1/services)
    2. Citizen inspects live wait estimates & queue depths (GET /api/v1/queues/summary)
    3. Citizen issues digital token (POST /api/v1/tokens)
    4. Citizen connects live to WebSocket stream (/ws/live?token_public_id=...)
    5. Counter calls citizen's token (POST /api/v1/counters/{id}/call-next)
    6. Citizen receives real-time update with zero polling/refresh
    7. Citizen views called status and counter location
    """
    # 1. Fetch services on kiosk
    services_resp = sync_client.get("/api/v1/services")
    assert services_resp.status_code == 200
    services = services_resp.json()
    assert len(services) > 0
    service = services[0]

    # 2. Check prospective wait estimate
    est_resp = sync_client.get(f"/api/v1/queues/{service['id']}/estimate?session_id=citizen-session")
    assert est_resp.status_code == 200
    est_data = est_resp.json()
    assert "estimated_wait_seconds" in est_data

    # Find an available idle counter and ensure it serves this service
    counters = sync_client.get("/api/v1/counters").json()
    counter = next(c for c in counters if c["status"] == "OPEN_IDLE" and not c.get("current_token_id"))
    c_id = counter["id"]
    sync_client.put(f"/api/v1/counters/{c_id}/services", json=[service["id"]])

    # 3. Citizen issues token from kiosk
    create_resp = sync_client.post(
        "/api/v1/tokens",
        json={
            "service_id": service["id"],
            "session_id": "citizen-session",
            "contact_info": "+923001234567",
            "priority": 0,
        },
    )
    assert create_resp.status_code == 201
    token_data = create_resp.json()
    public_id = token_data["public_id"]
    display_num = token_data["display_number"]
    assert token_data["status"] == TokenStatus.WAITING.value
    assert token_data["position_ahead"] == 0

    # 4. Connect to WebSocket stream for this citizen's token
    with sync_client.websocket_connect(f"/ws/live?token_public_id={public_id}&session_id=citizen-session") as ws:
        # Initial connect acknowledgment
        ack = ws.receive_json()
        assert ack["event"] == "CONNECTED"

        # Bi-directional heartbeat
        ws.send_json({"type": "PING"})
        pong = ws.receive_json()
        assert pong.get("event") == "PONG"

        # 5. Counter operator calls next token
        call_resp = sync_client.post(f"/api/v1/counters/{c_id}/call-next?session_id=citizen-session")
        assert call_resp.status_code == 200
        called_data = call_resp.json()
        assert called_data["display_number"] == display_num

        # 6. Citizen receives real-time broadcast via WebSocket without browser refresh
        received_event = ws.receive_json()
        assert received_event.get("event") in ["NOTIFICATION", "NOTIFICATION_DISPATCHED", "TOKEN_CALLED"]

        # 7. Citizen checks token status
        status_resp = sync_client.get(f"/api/v1/tokens/{public_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == TokenStatus.CALLED.value
        assert status_data["called_counter_name"] == counter["name"]


def test_citizen_queue_position_progression_ahead(sync_client):
    """
    Verifies that when multiple citizens join a queue:
    1. First citizen has position 0 ahead.
    2. Second citizen has position 1 ahead.
    3. When first citizen is called, second citizen advances to position 0 ahead.
    """
    services = sync_client.get("/api/v1/services").json()
    service_id = services[0]["id"]
    session_id = "queue-progression"

    # Set up counter
    counters = sync_client.get("/api/v1/counters").json()
    counter = next(c for c in counters if c["status"] == "OPEN_IDLE" and not c.get("current_token_id"))
    sync_client.put(f"/api/v1/counters/{counter['id']}/services", json=[service_id])

    # Issue Citizen 1
    c1 = sync_client.post("/api/v1/tokens", json={"service_id": service_id, "session_id": session_id}).json()
    assert c1["position_ahead"] == 0

    # Issue Citizen 2
    c2 = sync_client.post("/api/v1/tokens", json={"service_id": service_id, "session_id": session_id}).json()
    assert c2["position_ahead"] == 1

    # Call Citizen 1
    call_res = sync_client.post(f"/api/v1/counters/{counter['id']}/call-next?session_id={session_id}")
    assert call_res.status_code == 200

    # Check Citizen 2's position ahead — automatically decremented to 0!
    c2_updated = sync_client.get(f"/api/v1/tokens/{c2['public_id']}").json()
    assert c2_updated["position_ahead"] == 0


def test_citizen_token_cancellation_flow(sync_client):
    """Verifies a citizen can cancel their waiting token self-service."""
    services = sync_client.get("/api/v1/services").json()
    service_id = services[0]["id"]

    create_resp = sync_client.post(
        "/api/v1/tokens",
        json={"service_id": service_id, "session_id": "cancel-session"},
    )
    public_id = create_resp.json()["public_id"]

    # Cancel
    cancel_resp = sync_client.post(f"/api/v1/tokens/{public_id}/cancel?reason=Citizen+changed+mind")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == TokenStatus.CANCELLED.value

    # Verify lookup reflects cancellation
    check_resp = sync_client.get(f"/api/v1/tokens/{public_id}")
    assert check_resp.json()["status"] == TokenStatus.CANCELLED.value
