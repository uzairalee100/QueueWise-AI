"""
QueueWise AI — Wait Time Estimator Service

Calculates dynamic wait times and operational queue metrics based on:
1. Real queue depth (tokens ahead, respecting priority ordering)
2. Number of active service counters (OPEN_IDLE, OPEN_SERVING)
3. Historical service duration (rolling window average with fallback to configured default)

Formula:
    Estimated Wait = ((Position Ahead + 1) * Avg Service Duration) / max(1, Active Counters)
    When active counters == 0, the queue is marked as STALLED.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.token import Token
from app.models.enums import CounterStatus, TokenStatus
from app.schemas.queue import (
    QueueSummaryItem,
    QueueSummaryResponse,
    ServingTokenInfo,
    WaitEstimateDetail,
)
from app.services.queue_engine import QueueEngine
from app.core.logging import get_logger

logger = get_logger(__name__)


class WaitEstimator:
    """Service for estimating queue wait times and operational metrics."""

    @classmethod
    async def get_active_counters_for_service(
        cls,
        session: AsyncSession,
        service_category_id: uuid.UUID,
    ) -> List[Counter]:
        """
        Find all open counters (OPEN_IDLE or OPEN_SERVING) supporting the given service category.
        """
        stmt = (
            select(Counter)
            .options(selectinload(Counter.supported_services), selectinload(Counter.current_token))
            .where(
                and_(
                    Counter.status.in_([CounterStatus.OPEN_IDLE, CounterStatus.OPEN_SERVING]),
                    Counter.supported_services.any(ServiceCategory.id == service_category_id),
                )
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_total_counters_for_service(
        cls,
        session: AsyncSession,
        service_category_id: uuid.UUID,
    ) -> List[Counter]:
        """
        Find all counters that support the given service category, regardless of status.
        """
        stmt = (
            select(Counter)
            .options(selectinload(Counter.supported_services))
            .where(Counter.supported_services.any(ServiceCategory.id == service_category_id))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_average_service_duration(
        cls,
        session: AsyncSession,
        service_category_id: uuid.UUID,
        window_size: int = 20,
    ) -> Tuple[int, str, str]:
        """
        Calculate the average service duration in seconds for a service category.
        Uses a rolling average of recently completed tokens.
        Falls back to configured default duration or system baseline.

        Returns:
            Tuple of (avg_duration_seconds, calculation_basis, confidence_level)
        """
        # Query recently completed tokens with recorded timestamps
        stmt = (
            select(Token)
            .where(
                and_(
                    Token.service_category_id == service_category_id,
                    Token.status == TokenStatus.COMPLETED,
                    Token.service_started_at.is_not(None),
                    Token.completed_at.is_not(None),
                )
            )
            .order_by(Token.completed_at.desc())
            .limit(window_size)
        )
        result = await session.execute(stmt)
        completed_tokens = result.scalars().all()

        durations: List[float] = []
        for t in completed_tokens:
            if t.service_started_at and t.completed_at:
                sec = (t.completed_at - t.service_started_at).total_seconds()
                # Exclude extreme anomalies (< 5s or > 7200s)
                if 5.0 <= sec <= 7200.0:
                    durations.append(sec)

        if durations:
            avg_sec = round(sum(durations) / len(durations))
            confidence = "HIGH" if len(durations) >= 5 else "MEDIUM"
            return (avg_sec, "HISTORICAL_WINDOW", confidence)

        # Fallback to ServiceCategory configured default
        service = await session.get(ServiceCategory, service_category_id)
        if service and service.default_duration_seconds:
            confidence = "LOW"
            return (service.default_duration_seconds, "CONFIGURED_DEFAULT", confidence)

        # System-level fallback
        return (180, "FALLBACK_DEFAULT", "LOW")

    @classmethod
    async def estimate_token_wait(
        cls,
        session: AsyncSession,
        token: Token,
    ) -> Dict[str, Any]:
        """
        Calculate dynamic estimated wait time for an existing token.

        Returns a dictionary with:
            - position_ahead (int)
            - estimated_wait_seconds (int)
            - estimated_wait_minutes (float)
            - active_counters (int)
            - avg_service_duration_seconds (int)
            - is_stalled (bool)
            - calculation_basis (str)
            - confidence_level (str)
        """
        if token.status != TokenStatus.WAITING:
            # Token is already called, serving, completed, cancelled, or skipped
            return {
                "position_ahead": 0,
                "estimated_wait_seconds": 0,
                "estimated_wait_minutes": 0.0,
                "active_counters": 0,
                "avg_service_duration_seconds": 0,
                "is_stalled": False,
                "calculation_basis": "NON_WAITING_STATUS",
                "confidence_level": "HIGH",
            }

        # 1. Get queue position and tokens ahead (respects priority and creation time)
        _, ahead_count = await QueueEngine.get_queue_position_and_ahead(session, token)

        # 2. Get active counters for this service
        active_counters = await cls.get_active_counters_for_service(
            session, token.service_category_id
        )
        c_active = len(active_counters)

        # 3. Get average service duration
        avg_duration, basis, confidence = await cls.get_average_service_duration(
            session, token.service_category_id
        )

        # 4. Compute estimated wait
        if c_active == 0:
            is_stalled = True
            # No counters open: estimate assumes single-server queue when service resumes
            estimated_wait = (ahead_count + 1) * avg_duration
            confidence = "LOW"
        else:
            is_stalled = False
            # Dynamic multi-server formula: ((ahead_count + 1) * avg_duration) / active_counters
            estimated_wait = max(1, round(((ahead_count + 1) * avg_duration) / c_active))

        return {
            "position_ahead": ahead_count,
            "estimated_wait_seconds": estimated_wait,
            "estimated_wait_minutes": round(estimated_wait / 60.0, 1),
            "active_counters": c_active,
            "avg_service_duration_seconds": avg_duration,
            "is_stalled": is_stalled,
            "calculation_basis": basis,
            "confidence_level": confidence,
        }

    @classmethod
    async def estimate_prospective_arrival(
        cls,
        session: AsyncSession,
        service_category_id: uuid.UUID,
        session_id: str = "default",
        priority: int = 0,
    ) -> WaitEstimateDetail:
        """
        Estimate wait time for a prospective citizen arriving right now.
        Useful for pre-token kiosk displays and landing page expectations.
        """
        service = await session.get(ServiceCategory, service_category_id)
        if not service:
            raise ValueError(f"ServiceCategory with ID '{service_category_id}' not found.")

        # Count existing waiting tokens ahead for this service
        stmt = select(func.count(Token.id)).where(
            and_(
                Token.service_category_id == service_category_id,
                Token.session_id == session_id,
                Token.status == TokenStatus.WAITING,
                Token.priority >= priority,
            )
        )
        res = await session.execute(stmt)
        ahead_count = res.scalar() or 0

        # Get active counters
        active_counters = await cls.get_active_counters_for_service(session, service_category_id)
        c_active = len(active_counters)

        # Get average duration
        avg_duration, basis, confidence = await cls.get_average_service_duration(
            session, service_category_id
        )

        if c_active == 0:
            is_stalled = True
            estimated_wait = (ahead_count + 1) * avg_duration
            status_msg = "All counters currently closed or paused for this service. Queue is paused."
            confidence = "LOW"
        else:
            is_stalled = False
            has_idle = any(c.status == CounterStatus.OPEN_IDLE for c in active_counters)
            if ahead_count == 0 and has_idle:
                estimated_wait = 0
                status_msg = f"{c_active} counter(s) open. Immediate service available."
            else:
                estimated_wait = max(0, round(((ahead_count + 1) * avg_duration) / c_active))
                status_msg = f"{c_active} active counter(s). Queue moving steadily."

        return WaitEstimateDetail(
            service_id=service.id,
            service_name=service.name,
            service_code=service.code,
            position_ahead=ahead_count,
            active_counters=c_active,
            avg_service_duration_seconds=avg_duration,
            estimated_wait_seconds=estimated_wait,
            estimated_wait_minutes=round(estimated_wait / 60.0, 1),
            is_stalled=is_stalled,
            calculation_basis=basis,
            confidence_level=confidence,
            status_message=status_msg,
        )

    @classmethod
    async def get_queue_summary(
        cls,
        session: AsyncSession,
        session_id: str = "default",
    ) -> QueueSummaryResponse:
        """
        Generate operational queue summary across all active service categories.
        Includes live counter states, queue depths, and dynamic wait times.
        """
        # Fetch all active service categories
        services_stmt = (
            select(ServiceCategory)
            .where(ServiceCategory.is_active == True)
            .order_by(ServiceCategory.name.asc())
        )
        services_res = await session.execute(services_stmt)
        services = list(services_res.scalars().all())

        summary_items: List[QueueSummaryItem] = []
        total_waiting_all = 0
        total_serving_all = 0

        # Unique active counters overall
        all_active_counters_stmt = select(Counter).where(
            Counter.status.in_([CounterStatus.OPEN_IDLE, CounterStatus.OPEN_SERVING])
        )
        all_active_counters_res = await session.execute(all_active_counters_stmt)
        total_active_counters_overall = len(list(all_active_counters_res.scalars().all()))

        now = datetime.now(timezone.utc)

        for svc in services:
            # 1. Count tokens by status for this service
            status_stmt = (
                select(Token.status, func.count(Token.id))
                .where(
                    and_(
                        Token.service_category_id == svc.id,
                        Token.session_id == session_id,
                    )
                )
                .group_by(Token.status)
            )
            status_res = await session.execute(status_stmt)
            counts_map = dict(status_res.all())

            waiting_cnt = counts_map.get(TokenStatus.WAITING, 0)
            serving_cnt = counts_map.get(TokenStatus.SERVING, 0) + counts_map.get(TokenStatus.CALLED, 0)
            completed_cnt = counts_map.get(TokenStatus.COMPLETED, 0)
            skipped_cnt = counts_map.get(TokenStatus.SKIPPED, 0)
            cancelled_cnt = counts_map.get(TokenStatus.CANCELLED, 0)

            total_waiting_all += waiting_cnt
            total_serving_all += serving_cnt

            # 2. Get active counters and total counters for this service
            active_counters = await cls.get_active_counters_for_service(session, svc.id)
            total_counters = await cls.get_total_counters_for_service(session, svc.id)

            c_active = len(active_counters)
            c_total = len(total_counters)

            # 3. Get average duration & prospective wait estimate
            avg_duration, _, _ = await cls.get_average_service_duration(session, svc.id)

            if c_active == 0:
                is_stalled = waiting_cnt > 0
                estimated_wait = (waiting_cnt + 1) * avg_duration
                queue_status = "STALLED" if waiting_cnt > 0 else "NORMAL"
            else:
                is_stalled = False
                has_idle = any(c.status == CounterStatus.OPEN_IDLE for c in active_counters)
                if waiting_cnt == 0 and has_idle:
                    estimated_wait = 0
                else:
                    estimated_wait = max(0, round(((waiting_cnt + 1) * avg_duration) / c_active))

                if estimated_wait > 1800 or waiting_cnt > 15:
                    queue_status = "CONGESTED"
                elif waiting_cnt > 5:
                    queue_status = "BUSY"
                else:
                    queue_status = "NORMAL"

            # 4. Identify next token to be called
            next_token_stmt = (
                select(Token)
                .where(
                    and_(
                        Token.service_category_id == svc.id,
                        Token.session_id == session_id,
                        Token.status == TokenStatus.WAITING,
                    )
                )
                .order_by(Token.priority.desc(), Token.created_at.asc())
                .limit(1)
            )
            next_token_res = await session.execute(next_token_stmt)
            next_token = next_token_res.scalar_one_or_none()
            next_token_display = next_token.display_number if next_token else None

            # 5. Extract currently serving tokens at counters supporting this service
            currently_serving: List[ServingTokenInfo] = []
            for ac in active_counters:
                if ac.current_token and ac.current_token.service_category_id == svc.id:
                    elapsed = None
                    if ac.current_token.service_started_at:
                        elapsed = int((now - ac.current_token.service_started_at).total_seconds())
                    currently_serving.append(
                        ServingTokenInfo(
                            counter_id=ac.id,
                            counter_name=ac.name,
                            token_id=ac.current_token.id,
                            token_display_number=ac.current_token.display_number,
                            service_started_at=ac.current_token.service_started_at,
                            duration_seconds=elapsed,
                        )
                    )

            summary_items.append(
                QueueSummaryItem(
                    service_id=svc.id,
                    service_name=svc.name,
                    service_code=svc.code,
                    waiting_count=waiting_cnt,
                    serving_count=serving_cnt,
                    completed_count=completed_cnt,
                    skipped_count=skipped_cnt,
                    cancelled_count=cancelled_cnt,
                    active_counters=c_active,
                    total_counters=c_total,
                    avg_service_duration_seconds=avg_duration,
                    estimated_wait_for_next_arrival=estimated_wait,
                    is_stalled=is_stalled,
                    queue_status=queue_status,
                    next_token_display_number=next_token_display,
                    currently_serving=currently_serving,
                )
            )

        return QueueSummaryResponse(
            session_id=session_id,
            timestamp=now,
            total_waiting=total_waiting_all,
            total_serving=total_serving_all,
            total_active_counters=total_active_counters_overall,
            services=summary_items,
        )
