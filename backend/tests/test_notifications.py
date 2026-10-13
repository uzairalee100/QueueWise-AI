"""
QueueWise AI — Notification System Tests

Validates Milestone 4 notification requirements:
1. Notification creation on token generation.
2. Notification dispatch when token is called to counter.
3. Approaching notification trigger when queue position <= threshold.
4. Notifications for completion and skip.
5. In-app notifications retrieval endpoint (GET /api/v1/tokens/{public_id}/notifications).
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.service_category import ServiceCategory
from app.models.token import Token
from app.models.enums import NotificationType, TokenStatus
from app.services.notification_service import NotificationService


@pytest.mark.anyio
async def test_token_creation_triggers_notification(client: AsyncClient):
    """Creating a token generates and persists a CREATED notification."""
    res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "notif-test-1"},
    )
    assert res.status_code == 201
    token_data = res.json()
    public_id = token_data["public_id"]

    # Retrieve notifications for this token
    notif_res = await client.get(f"/api/v1/tokens/{public_id}/notifications")
    assert notif_res.status_code == 200
    notifications = notif_res.json()

    assert len(notifications) >= 1
    created_notif = next(n for n in notifications if n["type"] == "CREATED")
    assert "Token Issued" in created_notif["title"]
    assert token_data["display_number"] in created_notif["message"]
    assert created_notif["status"] == "SENT"


@pytest.mark.anyio
async def test_token_called_triggers_called_notification(client: AsyncClient):
    """Calling a token to counter generates a CALLED notification."""
    # Create token
    tok_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "notif-call-test"},
    )
    assert tok_res.status_code == 201
    public_id = tok_res.json()["public_id"]

    # Get an open counter
    counters = (await client.get("/api/v1/counters")).json()
    counter = next(c for c in counters if c["status"] == "OPEN_IDLE")
    c_id = counter["id"]

    # Call token
    call_res = await client.post(f"/api/v1/counters/{c_id}/call-next?session_id=notif-call-test")
    assert call_res.status_code == 200

    # Verify CALLED notification exists
    notif_res = await client.get(f"/api/v1/tokens/{public_id}/notifications")
    notifications = notif_res.json()
    called_notif = next(n for n in notifications if n["type"] == "CALLED")

    assert "Your Turn" in called_notif["title"]
    assert counter["name"] in called_notif["message"]


@pytest.mark.anyio
async def test_approaching_notification_rule_trigger(client: AsyncClient, db_session: AsyncSession):
    """
    Approaching notification is triggered for upcoming tokens when position ahead <= threshold.
    """
    svc_stmt = select(ServiceCategory).where(ServiceCategory.code == "GEN")
    svc_res = await db_session.execute(svc_stmt)
    gen_svc = svc_res.scalar_one()

    # Create 3 tokens
    tokens = []
    for i in range(3):
        res = await client.post(
            "/api/v1/tokens",
            json={"service_code": "GEN", "session_id": "approaching-test"},
        )
        assert res.status_code == 201
        tokens.append(res.json())

    # Check approaching triggers with threshold=2 (all 3 tokens have position <= 2)
    new_notifs = await NotificationService.check_and_notify_approaching_tokens(
        session=db_session,
        service_category_id=gen_svc.id,
        session_id="approaching-test",
        threshold=2,
    )
    assert len(new_notifs) == 3

    # Check that approaching notifications appear in the endpoint
    t0_notifs = (await client.get(f"/api/v1/tokens/{tokens[0]['public_id']}/notifications")).json()
    has_appr = any(n["type"] == "APPROACHING" for n in t0_notifs)
    assert has_appr is True

    # Calling check_and_notify_approaching_tokens again should NOT duplicate
    duplicate_notifs = await NotificationService.check_and_notify_approaching_tokens(
        session=db_session,
        service_category_id=gen_svc.id,
        session_id="approaching-test",
        threshold=2,
    )
    assert len(duplicate_notifs) == 0


@pytest.mark.anyio
async def test_token_completed_and_skipped_notifications(client: AsyncClient):
    """Complete and skip actions dispatch appropriate notifications."""
    # 1. Test complete
    tok1_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "test-comp-skip"},
    )
    tok1 = tok1_res.json()

    counters = (await client.get("/api/v1/counters")).json()
    c_id = counters[0]["id"]
    await client.post(f"/api/v1/counters/{c_id}/open")

    await client.post(f"/api/v1/counters/{c_id}/call-next?session_id=test-comp-skip")
    await client.post(f"/api/v1/counters/{c_id}/serve")
    await client.post(f"/api/v1/counters/{c_id}/complete")

    notifs1 = (await client.get(f"/api/v1/tokens/{tok1['public_id']}/notifications")).json()
    assert any(n["type"] == "COMPLETED" for n in notifs1)

    # 2. Test skip
    tok2_res = await client.post(
        "/api/v1/tokens",
        json={"service_code": "GEN", "session_id": "test-comp-skip"},
    )
    tok2 = tok2_res.json()

    await client.post(f"/api/v1/counters/{c_id}/call-next?session_id=test-comp-skip")
    await client.post(f"/api/v1/counters/{c_id}/skip?reason=Citizen+unreachable")

    notifs2 = (await client.get(f"/api/v1/tokens/{tok2['public_id']}/notifications")).json()
    skip_notif = next(n for n in notifs2 if n["type"] == "SKIPPED")
    assert "Citizen unreachable" in skip_notif["message"]
