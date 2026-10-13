"""
QueueWise AI — Token API Endpoints

Citizen-facing token issuance, tracking, and cancellation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.token import TokenCreate, TokenPublicStatus, TokenResponse
from app.services.queue_engine import (
    QueueEngine,
    TokenNotFoundError,
    ServiceCategoryNotFoundError,
    InvalidStateTransitionError,
)
from app.models.enums import TokenStatus

router = APIRouter()


@router.post("", response_model=TokenPublicStatus, status_code=status.HTTP_201_CREATED)
async def create_token(
    payload: TokenCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a new queue token for a service category.
    Supports idempotency via 'idempotency_key'.
    """
    try:
        token = await QueueEngine.create_token(
            session=db,
            service_category_id=payload.service_id,
            service_code=payload.service_code,
            session_id=payload.session_id or "default",
            contact_info=payload.contact_info,
            idempotency_key=payload.idempotency_key,
            priority=payload.priority,
        )

        position, ahead_count = await QueueEngine.get_queue_position_and_ahead(db, token)
        duration_per_token = (
            token.service_category.default_duration_seconds if token.service_category else 300
        )
        estimated_wait = (ahead_count + 1) * duration_per_token if token.status == TokenStatus.WAITING else 0

        return TokenPublicStatus(
            public_id=token.public_id,
            display_number=token.display_number,
            status=token.status,
            service_name=token.service_category.name if token.service_category else "General",
            service_code=token.service_category.code if token.service_category else "GEN",
            position_ahead=ahead_count,
            estimated_wait_seconds=estimated_wait,
            called_counter_name=token.called_counter.name if token.called_counter else None,
            created_at=token.created_at,
            called_at=token.called_at,
            session_id=token.session_id,
        )
    except ServiceCategoryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to issue token: {str(e)}",
        )


@router.get("/{public_id}", response_model=TokenPublicStatus)
async def get_token_status(
    public_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public token status endpoint for citizens.
    Returns live position in queue and calculated estimated wait time.
    """
    try:
        token = await QueueEngine.get_token_by_public_id(db, public_id)
        position, ahead_count = await QueueEngine.get_queue_position_and_ahead(db, token)
        duration_per_token = (
            token.service_category.default_duration_seconds if token.service_category else 300
        )
        estimated_wait = (ahead_count + 1) * duration_per_token if token.status == TokenStatus.WAITING else 0

        return TokenPublicStatus(
            public_id=token.public_id,
            display_number=token.display_number,
            status=token.status,
            service_name=token.service_category.name if token.service_category else "General",
            service_code=token.service_category.code if token.service_category else "GEN",
            position_ahead=ahead_count,
            estimated_wait_seconds=estimated_wait,
            called_counter_name=token.called_counter.name if token.called_counter else None,
            created_at=token.created_at,
            called_at=token.called_at,
            session_id=token.session_id,
        )
    except TokenNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token with ID '{public_id}' not found.",
        )


@router.post("/{public_id}/cancel", response_model=TokenPublicStatus)
async def cancel_token(
    public_id: str,
    reason: str = "Citizen cancelled",
    db: AsyncSession = Depends(get_db),
):
    """
    Citizen voluntarily cancels their waiting token.
    """
    try:
        token = await QueueEngine.cancel_token(db, public_id=public_id, reason=reason)
        return TokenPublicStatus(
            public_id=token.public_id,
            display_number=token.display_number,
            status=token.status,
            service_name=token.service_category.name if token.service_category else "General",
            service_code=token.service_category.code if token.service_category else "GEN",
            position_ahead=0,
            estimated_wait_seconds=0,
            called_counter_name=None,
            created_at=token.created_at,
            called_at=token.called_at,
            session_id=token.session_id,
        )
    except TokenNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token with ID '{public_id}' not found.",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
