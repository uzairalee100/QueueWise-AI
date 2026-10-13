"""
QueueWise AI — Queues API Router

Operational metrics, real-time queue summaries, and prospective wait estimations.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.queue import (
    QueueSummaryResponse,
    WaitEstimateDetail,
)
from app.schemas.token import TokenPublicStatus
from app.services.wait_estimator import WaitEstimator
from app.services.queue_engine import QueueEngine

router = APIRouter()


@router.get("/summary", response_model=QueueSummaryResponse)
async def get_queue_summary(
    session_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    """
    Get live operational summary for all active service queues.
    Includes active counters, queue depth, average service times,
    and arrival wait predictions.
    """
    try:
        summary = await WaitEstimator.get_queue_summary(db, session_id=session_id)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch queue summary: {str(e)}",
        )


@router.get("/{service_id}/estimate", response_model=WaitEstimateDetail)
async def get_prospective_wait_estimate(
    service_id: uuid.UUID,
    session_id: str = "default",
    priority: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate dynamic wait estimate for a citizen considering joining this queue now.
    Accounts for queue depth, active counters, and historical service durations.
    """
    try:
        estimate = await WaitEstimator.estimate_prospective_arrival(
            session=db,
            service_category_id=service_id,
            session_id=session_id,
            priority=priority,
        )
        return estimate
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate prospective estimate: {str(e)}",
        )


@router.get("/{service_id}/waiting", response_model=List[TokenPublicStatus])
async def get_waiting_tokens_for_service(
    service_id: uuid.UUID,
    session_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all waiting tokens for a specific service queue,
    ordered by priority and queue arrival, with live wait estimates.
    """
    try:
        tokens = await QueueEngine.get_waiting_tokens(
            session=db,
            service_category_id=service_id,
            session_id=session_id,
        )

        results = []
        for token in tokens:
            est = await WaitEstimator.estimate_token_wait(db, token)
            results.append(
                TokenPublicStatus(
                    public_id=token.public_id,
                    display_number=token.display_number,
                    status=token.status,
                    service_name=token.service_category.name if token.service_category else "General",
                    service_code=token.service_category.code if token.service_category else "GEN",
                    position_ahead=est["position_ahead"],
                    estimated_wait_seconds=est["estimated_wait_seconds"],
                    active_counters=est["active_counters"],
                    is_stalled=est["is_stalled"],
                    called_counter_name=token.called_counter.name if token.called_counter else None,
                    created_at=token.created_at,
                    called_at=token.called_at,
                    session_id=token.session_id,
                )
            )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch waiting tokens: {str(e)}",
        )
