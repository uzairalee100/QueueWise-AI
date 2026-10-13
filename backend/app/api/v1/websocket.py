"""
QueueWise AI — Real-Time WebSocket Router

Provides live WebSocket streaming for citizens, counter operators,
public queue displays, and supervisory dashboards.
"""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket import ws_manager
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/live")
async def websocket_live_stream(
    websocket: WebSocket,
    session_id: str = "default",
    token_public_id: Optional[str] = None,
    counter_id: Optional[str] = None,
):
    """
    WebSocket endpoint for real-time queue events, counter updates, and notifications.
    Supports query parameters:
      - session_id: Filter events by operational session (default: "default")
      - token_public_id: Subscribes specifically to a citizen's token alerts
      - counter_id: Subscribes to a specific counter's operator channel
    """
    await ws_manager.connect(
        websocket=websocket,
        session_id=session_id,
        token_public_id=token_public_id,
        counter_id=counter_id,
    )
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                msg_type = msg.get("type") or msg.get("event")
                if msg_type == "PING":
                    await ws_manager.send_personal_message(
                        websocket,
                        {
                            "event": "PONG",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("websocket_connection_terminated", error=str(e))
        ws_manager.disconnect(websocket)
