"""
QueueWise AI — WebSocket Connection Manager

Manages real-time WebSocket connections, session topics, client subscriptions,
and event multicasting across citizen portals and staff operator dashboards.
"""
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Centralized manager for WebSocket connections and event broadcasting."""

    def __init__(self):
        # Maps active WebSocket instances to client metadata
        self._connections: Dict[WebSocket, Dict[str, Any]] = {}

    @property
    def total_connections(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str = "default",
        token_public_id: Optional[str] = None,
        counter_id: Optional[str] = None,
    ) -> None:
        """Accept a new WebSocket connection and store client metadata."""
        await websocket.accept()
        now = datetime.now(timezone.utc)
        self._connections[websocket] = {
            "session_id": session_id,
            "token_public_id": token_public_id,
            "counter_id": counter_id,
            "connected_at": now.isoformat(),
        }
        logger.info(
            "websocket_connected",
            session_id=session_id,
            token_public_id=token_public_id,
            counter_id=counter_id,
            total=len(self._connections),
        )

        # Send connection confirmation to client
        await self.send_personal_message(
            websocket,
            {
                "event": "CONNECTED",
                "timestamp": now.isoformat(),
                "session_id": session_id,
                "data": {
                    "message": "Connected to QueueWise AI real-time event stream",
                    "subscribed_token": token_public_id,
                    "subscribed_counter": counter_id,
                },
            },
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if websocket in self._connections:
            meta = self._connections.pop(websocket)
            logger.info(
                "websocket_disconnected",
                session_id=meta.get("session_id"),
                total=len(self._connections),
            )

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send message directly to a specific socket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning("websocket_send_failed", error=str(e))
            self.disconnect(websocket)

    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> None:
        """
        Multicast an event to connected clients.
        If session_id is provided, sends to clients connected to that session or global.
        """
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "event": event,
            "timestamp": now,
            "session_id": session_id or "default",
            "data": data,
        }
        message_str = json.dumps(payload)

        dead_connections: List[WebSocket] = []
        for ws, meta in list(self._connections.items()):
            # Match session_id (if specified) or send to all if matching or global
            client_session = meta.get("session_id")
            if session_id and client_session and client_session != session_id:
                continue

            try:
                await ws.send_text(message_str)
            except Exception as e:
                logger.debug("websocket_broadcast_error", error=str(e))
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws)

    async def broadcast_to_token(
        self,
        token_public_id: str,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Send an event targeted at a specific token (e.g. citizen private notifications).
        Also broadcasts to session level so boards and dashboards can react.
        """
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "event": event,
            "timestamp": now,
            "token_public_id": token_public_id,
            "data": data,
        }
        message_str = json.dumps(payload)

        dead_connections: List[WebSocket] = []
        for ws, meta in list(self._connections.items()):
            target_token = meta.get("token_public_id")
            # Deliver if client is either this specific token OR subscribed to all/session
            if target_token is None or target_token == token_public_id:
                try:
                    await ws.send_text(message_str)
                except Exception:
                    dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws)


# Global singleton instance
ws_manager = ConnectionManager()
