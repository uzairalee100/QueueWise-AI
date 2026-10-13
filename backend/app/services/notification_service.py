"""
QueueWise AI — Notification Service

Handles notification generation, database persistence, rule-based alerts,
and real-time dispatching via WebSocket channels.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.token import Token
from app.models.enums import (
    NotificationType,
    NotificationChannel,
    NotificationStatus,
    TokenStatus,
)
from app.core.websocket import ws_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for issuing and dispatching citizen notifications."""

    @classmethod
    async def create_and_dispatch(
        cls,
        session: AsyncSession,
        token: Token,
        notification_type: NotificationType,
        message: str,
        title: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        """
        Create a notification record in the database and multicast it via WebSocket.
        """
        now = datetime.now(timezone.utc)
        notification = Notification(
            token_id=token.id,
            type=notification_type,
            channel=channel,
            status=NotificationStatus.SENT,
            title=title or notification_type.value.capitalize(),
            message=message,
            created_at=now,
            sent_at=now,
        )
        session.add(notification)
        await session.flush()

        logger.info(
            "notification_created",
            token_id=str(token.id),
            display_number=token.display_number,
            type=notification_type.value,
        )

        # Broadcast via WebSocket
        payload = {
            "notification_id": str(notification.id),
            "token_id": str(token.id),
            "token_public_id": token.public_id,
            "display_number": token.display_number,
            "type": notification.type.value,
            "channel": notification.channel.value,
            "title": notification.title,
            "message": notification.message,
            "timestamp": now.isoformat(),
        }

        # Send to token-specific listeners and session-level broadcast
        await ws_manager.broadcast_to_token(
            token_public_id=token.public_id,
            event="NOTIFICATION_DISPATCHED",
            data=payload,
        )

        return notification

    @classmethod
    async def notify_token_created(
        cls,
        session: AsyncSession,
        token: Token,
        position_ahead: int,
        estimated_wait_seconds: int,
    ) -> Notification:
        """Issue notification when token is first generated."""
        wait_min = round(estimated_wait_seconds / 60.0, 1)
        title = "Token Issued"
        msg = (
            f"Token {token.display_number} confirmed. "
            f"Queue position: #{position_ahead + 1}. Estimated wait: ~{wait_min} min."
        )
        return await cls.create_and_dispatch(
            session=session,
            token=token,
            notification_type=NotificationType.CREATED,
            title=title,
            message=msg,
        )

    @classmethod
    async def notify_token_called(
        cls,
        session: AsyncSession,
        token: Token,
        counter_name: str,
    ) -> Notification:
        """Issue high-priority notification when token is called to counter."""
        title = "Your Turn — Please Step Up"
        msg = f"Token {token.display_number} is called to {counter_name}! Please proceed to the counter now."
        return await cls.create_and_dispatch(
            session=session,
            token=token,
            notification_type=NotificationType.CALLED,
            title=title,
            message=msg,
        )

    @classmethod
    async def notify_token_completed(
        cls,
        session: AsyncSession,
        token: Token,
    ) -> Notification:
        """Issue completion confirmation notification."""
        title = "Service Completed"
        msg = f"Service for token {token.display_number} completed. Thank you!"
        return await cls.create_and_dispatch(
            session=session,
            token=token,
            notification_type=NotificationType.COMPLETED,
            title=title,
            message=msg,
        )

    @classmethod
    async def notify_token_skipped(
        cls,
        session: AsyncSession,
        token: Token,
        reason: Optional[str] = None,
    ) -> Notification:
        """Issue notification when token is skipped."""
        title = "Token Skipped"
        msg = f"Token {token.display_number} was skipped: {reason or 'Absent when called'}. Speak to reception if present."
        return await cls.create_and_dispatch(
            session=session,
            token=token,
            notification_type=NotificationType.SKIPPED,
            title=title,
            message=msg,
        )

    @classmethod
    async def check_and_notify_approaching_tokens(
        cls,
        session: AsyncSession,
        service_category_id: uuid.UUID,
        session_id: str = "default",
        threshold: int = 2,
    ) -> List[Notification]:
        """
        Rule trigger: Check waiting queue for this service.
        For any waiting token with position_ahead <= threshold, issue an APPROACHING
        notification if one hasn't been created yet.
        """
        # Fetch all waiting tokens for this service ordered by priority and time
        stmt = (
            select(Token)
            .where(
                and_(
                    Token.service_category_id == service_category_id,
                    Token.session_id == session_id,
                    Token.status == TokenStatus.WAITING,
                )
            )
            .order_by(Token.priority.desc(), Token.created_at.asc())
            .options(selectinload(Token.notifications))
        )
        res = await session.execute(stmt)
        waiting_tokens = list(res.scalars().all())

        new_notifications: List[Notification] = []
        for ahead_idx, token in enumerate(waiting_tokens):
            if ahead_idx <= threshold:
                # Check if an APPROACHING notification already exists
                has_approaching = any(
                    n.type == NotificationType.APPROACHING for n in token.notifications
                )
                if not has_approaching:
                    title = "Almost Your Turn!"
                    msg = (
                        f"Get ready! Only {ahead_idx} person{'s' if ahead_idx != 1 else ''} ahead "
                        f"of token {token.display_number}. Please remain near the counter area."
                    )
                    notif = await cls.create_and_dispatch(
                        session=session,
                        token=token,
                        notification_type=NotificationType.APPROACHING,
                        title=title,
                        message=msg,
                    )
                    new_notifications.append(notif)

        return new_notifications

    @classmethod
    async def get_token_notifications(
        cls,
        session: AsyncSession,
        token_public_id: str,
    ) -> List[Notification]:
        """Retrieve all notification history for a token by public_id."""
        stmt = (
            select(Notification)
            .join(Token, Token.id == Notification.token_id)
            .where(Token.public_id == token_public_id)
            .order_by(Notification.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())
