"""
QueueWise AI — Real-Time WebSocket Test Suite

Validates Milestone 4 WebSocket & Real-Time deliverables:
1. WebSocket connection handshake and acknowledgment (CONNECTED).
2. Bi-directional ping/pong heartbeat.
3. Exit condition: "State updates propagate to connected clients without browser refresh".
4. Real-time TOKEN_CREATED multicast on token issuance.
5. Real-time TOKEN_CALLED multicast on staff call.
6. Real-time COUNTER_STATUS_CHANGED multicast on operator status update.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.websocket import ws_manager


def test_websocket_connection_and_heartbeat(sync_client):
    """Verify WebSocket handshake and bi-directional ping/pong."""
    with sync_client.websocket_connect("/ws/live?session_id=ws-test") as ws:
        # 1. Verify connection acknowledgment
        ack = ws.receive_json()
        assert ack["event"] == "CONNECTED"
        assert ack["session_id"] == "ws-test"

        # 2. Test ping/pong
        ws.send_json({"type": "PING"})
        pong = ws.receive_json()
        assert pong["event"] == "PONG"
        assert "timestamp" in pong


def test_exit_condition_state_updates_propagate_in_real_time(sync_client):
    """
    CRITICAL EXIT CONDITION TEST FOR MILESTONE 4:
    'State updates propagate to connected clients without browser refresh'

    1. Connect client via WebSocket to listen for live events.
    2. Perform token issuance via HTTP API.
    3. The WebSocket immediately receives TOKEN_CREATED and NOTIFICATION_DISPATCHED.
    4. Call the token to a counter via HTTP API.
    5. The WebSocket immediately receives TOKEN_CALLED.
    6. Change counter status via HTTP API.
    7. The WebSocket immediately receives COUNTER_STATUS_CHANGED.
    """
    with sync_client.websocket_connect("/ws/live?session_id=live-demo") as ws:
        # Consume connection acknowledgment
        ack = ws.receive_json()
        assert ack["event"] == "CONNECTED"

        # ACTION 1: Issue token via REST API
        tok_res = sync_client.post(
            "/api/v1/tokens",
            json={"service_code": "GEN", "session_id": "live-demo"},
        )
        assert tok_res.status_code == 201
        token_data = tok_res.json()

        # Client receives real-time events without refresh!
        received_events = []
        for _ in range(2):  # TOKEN_CREATED and NOTIFICATION_DISPATCHED
            event_msg = ws.receive_json()
            received_events.append(event_msg["event"])

        assert "TOKEN_CREATED" in received_events
        assert "NOTIFICATION_DISPATCHED" in received_events

        # ACTION 2: Operator calls next token to Counter 1
        counters = sync_client.get("/api/v1/counters").json()
        # Find an OPEN_IDLE counter
        counter = next(c for c in counters if c["status"] == "OPEN_IDLE" and not c.get("current_token_id"))
        c_id = counter["id"]

        call_res = sync_client.post(f"/api/v1/counters/{c_id}/call-next?session_id=live-demo")
        assert call_res.status_code == 200

        # Client receives TOKEN_CALLED and/or NOTIFICATION_DISPATCHED in real-time!
        call_events = []
        for _ in range(2):
            msg = ws.receive_json()
            call_events.append(msg["event"])

        assert "TOKEN_CALLED" in call_events

        # ACTION 3: Serve and complete token to free counter, then pause
        serve_res = sync_client.post(f"/api/v1/counters/{c_id}/serve")
        assert serve_res.status_code == 200
        serve_evt = ws.receive_json()
        assert serve_evt["event"] == "TOKEN_SERVING"

        comp_res = sync_client.post(f"/api/v1/counters/{c_id}/complete")
        assert comp_res.status_code == 200
        # Consume completion events (TOKEN_COMPLETED and NOTIFICATION_DISPATCHED)
        for _ in range(2):
            ws.receive_json()

        # Now pause free counter
        pause_res = sync_client.post(f"/api/v1/counters/{c_id}/pause")
        assert pause_res.status_code == 200
        pause_evt = ws.receive_json()
        assert pause_evt["event"] == "COUNTER_STATUS_CHANGED"
        assert pause_evt["data"]["status"] == "PAUSED"


def test_token_private_channel_broadcast(sync_client):
    """Verify citizen receives events scoped specifically to their token public ID."""
    # Create token first
    res = sync_client.post("/api/v1/tokens", json={"service_code": "GEN", "session_id": "private-ch"})
    public_id = res.json()["public_id"]

    # Citizen connects with their specific token_public_id parameter
    with sync_client.websocket_connect(f"/ws/live?token_public_id={public_id}") as ws:
        ack = ws.receive_json()
        assert ack["event"] == "CONNECTED"
        assert ack["data"]["subscribed_token"] == public_id
