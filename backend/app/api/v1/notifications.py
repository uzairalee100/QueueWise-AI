"""
QueueWise AI — Notifications API Router

Citizen notification retrieval, test dispatching, and alert history.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/{token_public_id}", response_model=List[NotificationResponse])
async def get_notifications_for_token(
    token_public_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all in-app notifications dispatched for a specific token.
    """
    try:
        notifications = await NotificationService.get_token_notifications(
            session=db, token_public_id=token_public_id
        )
        return notifications
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )
