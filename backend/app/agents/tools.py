"""
QueueWise AI — AI Operations Agent Tools

Read-only tools that gather live queue metrics, analytics, and optimization
recommendations from the database. These tools are the agent's "eyes" into
the operational state — the agent never modifies queue state directly.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.token import Token
from app.models.counter import Counter
from app.models.service_category import ServiceCategory
from app.models.service_event import ServiceEvent
from app.models.enums import TokenStatus, CounterStatus, ServiceEventType
from app.services.analytics_service import AnalyticsService
from app.simulation.optimizer import CounterOptimizer
from app.core.logging import get_logger

logger = get_logger(__name__)


async def tool_get_queue_snapshot(session: AsyncSession, session_id: str = "default") -> Dict[str, Any]:
    """
    Get a real-time snapshot of queue state: waiting counts, serving counts,
    counter statuses, and stall indicators per service category.
    """
    # Service categories
    cat_stmt = select(ServiceCategory).where(ServiceCategory.is_active.is_(True))
    cat_res = await session.execute(cat_stmt)
    categories = list(cat_res.scalars().all())

    # Tokens
    token_stmt = select(Token).where(
        Token.simulation_run_id.is_(None),
        Token.session_id == session_id,
    )
    token_res = await session.execute(token_stmt)
    tokens = list(token_res.scalars().all())

    # Counters
    counter_stmt = select(Counter)
    counter_res = await session.execute(counter_stmt)
    counters = list(counter_res.scalars().all())

    # Aggregate per service
    services_snapshot = []
    for cat in categories:
        cat_tokens = [t for t in tokens if t.service_category_id == cat.id]
        waiting = sum(1 for t in cat_tokens if t.status == TokenStatus.WAITING)
        serving = sum(1 for t in cat_tokens if t.status == TokenStatus.SERVING)
        called = sum(1 for t in cat_tokens if t.status == TokenStatus.CALLED)
        completed = sum(1 for t in cat_tokens if t.status == TokenStatus.COMPLETED)
        skipped = sum(1 for t in cat_tokens if t.status == TokenStatus.SKIPPED)
        cancelled = sum(1 for t in cat_tokens if t.status == TokenStatus.CANCELLED)

        # Wait times of completed tokens
        wait_times = []
        for t in cat_tokens:
            if t.called_at and t.created_at:
                wt = (t.called_at - t.created_at).total_seconds()
                wait_times.append(max(0.0, wt))

        avg_wait = round(sum(wait_times) / len(wait_times)) if wait_times else 0

        services_snapshot.append({
            "service_code": cat.code,
            "service_name": cat.name,
            "waiting": waiting,
            "called": called,
            "serving": serving,
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "avg_wait_seconds": avg_wait,
            "default_duration_seconds": cat.default_duration_seconds,
        })

    # Counter summary
    counters_snapshot = []
    active_count = 0
    for c in counters:
        is_active = c.status in (CounterStatus.OPEN_IDLE, CounterStatus.OPEN_SERVING)
        if is_active:
            active_count += 1
        counters_snapshot.append({
            "name": c.name,
            "status": c.status.value,
            "is_active": is_active,
            "current_token_id": str(c.current_token_id) if c.current_token_id else None,
        })

    total_waiting = sum(s["waiting"] for s in services_snapshot)
    total_serving = sum(s["serving"] for s in services_snapshot)
    is_stalled = total_waiting > 0 and active_count == 0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "total_waiting": total_waiting,
        "total_serving": total_serving,
        "active_counters": active_count,
        "total_counters": len(counters),
        "is_stalled": is_stalled,
        "services": services_snapshot,
        "counters": counters_snapshot,
    }


async def tool_get_analytics_summary(
    session: AsyncSession,
    hours_back: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch computed analytics summary metrics from the AnalyticsService.
    Returns KPIs, wait times, SLA compliance, and counter utilization.
    """
    start_time = None
    if hours_back and hours_back > 0:
        from datetime import timedelta
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    summary = await AnalyticsService.get_summary_metrics(
        session=session,
        start_time=start_time,
    )
    return summary.model_dump()


async def tool_get_optimization_recommendation(
    session: AsyncSession,
    session_id: str = "default",
    total_counters: Optional[int] = None,
    target_sla_seconds: float = 600.0,
) -> Dict[str, Any]:
    """
    Run the M/M/c counter allocation optimizer with live data
    and return recommendations for counter reallocation.
    """
    # Get service categories
    cat_stmt = select(ServiceCategory).where(ServiceCategory.is_active.is_(True))
    cat_res = await session.execute(cat_stmt)
    categories = list(cat_res.scalars().all())

    # Get tokens to compute arrival rates
    token_stmt = select(Token).where(
        Token.simulation_run_id.is_(None),
        Token.session_id == session_id,
    )
    token_res = await session.execute(token_stmt)
    tokens = list(token_res.scalars().all())

    # Get counters
    counter_stmt = select(Counter)
    counter_res = await session.execute(counter_stmt)
    counters = list(counter_res.scalars().all())

    if total_counters is None:
        total_counters = len(counters)

    # Build service data for optimizer
    services_data = []
    for cat in categories:
        cat_tokens = [t for t in tokens if t.service_category_id == cat.id]
        total_count = len(cat_tokens)

        # Compute arrival rate: tokens per minute based on time window
        if total_count > 1:
            created_times = sorted([t.created_at for t in cat_tokens if t.created_at])
            if len(created_times) >= 2:
                time_span = (created_times[-1] - created_times[0]).total_seconds()
                arrival_rate = (total_count / max(60, time_span)) * 60
            else:
                arrival_rate = 1.0
        else:
            arrival_rate = max(0.5, total_count)

        # Compute average service duration from completed tokens
        durations = [
            (t.completed_at - t.service_started_at).total_seconds()
            for t in cat_tokens
            if t.status == TokenStatus.COMPLETED and t.completed_at and t.service_started_at
        ]
        avg_duration = sum(durations) / len(durations) if durations else cat.default_duration_seconds

        # Count current counters serving this service type
        current_counters = max(1, sum(
            1 for c in counters
            if c.status in (CounterStatus.OPEN_IDLE, CounterStatus.OPEN_SERVING)
        ) // max(1, len(categories)))

        services_data.append({
            "code": cat.code,
            "name": cat.name,
            "arrival_rate_per_min": round(arrival_rate, 2),
            "avg_duration_seconds": round(avg_duration),
            "current_counters": current_counters,
        })

    result = CounterOptimizer.optimize_allocation(
        services=services_data,
        total_counters=total_counters,
        target_sla_seconds=target_sla_seconds,
    )
    return result


async def tool_get_bottleneck_analysis(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Identify queue bottlenecks: services with excessively long waits,
    stalled queues, or underutilized counters.
    """
    snapshot = await tool_get_queue_snapshot(session, session_id)
    services = snapshot.get("services", [])

    bottlenecks = []
    underutilized = []
    alerts = []

    for s in services:
        code = s["service_code"]
        name = s["service_name"]
        waiting = s["waiting"]
        serving = s["serving"]
        avg_wait = s["avg_wait_seconds"]

        # Bottleneck detection
        if waiting > 10:
            bottlenecks.append({
                "service_code": code,
                "service_name": name,
                "severity": "HIGH" if waiting > 20 else "MEDIUM",
                "reason": f"{waiting} citizens waiting with avg wait of {avg_wait}s",
                "waiting": waiting,
                "avg_wait_seconds": avg_wait,
            })
        elif waiting > 5:
            bottlenecks.append({
                "service_code": code,
                "service_name": name,
                "severity": "LOW",
                "reason": f"{waiting} citizens in queue",
                "waiting": waiting,
                "avg_wait_seconds": avg_wait,
            })

        if serving == 0 and waiting == 0:
            underutilized.append({
                "service_code": code,
                "service_name": name,
                "reason": "No active demand — counters may be reassigned",
            })

    if snapshot["is_stalled"]:
        alerts.append({
            "level": "CRITICAL",
            "message": f"System stalled: {snapshot['total_waiting']} citizens waiting but 0 active counters!",
        })

    if snapshot["total_waiting"] > 30:
        alerts.append({
            "level": "WARNING",
            "message": f"High load: {snapshot['total_waiting']} total citizens waiting across all services.",
        })

    return {
        "timestamp": snapshot["timestamp"],
        "bottlenecks": bottlenecks,
        "underutilized_services": underutilized,
        "alerts": alerts,
        "snapshot_summary": {
            "total_waiting": snapshot["total_waiting"],
            "total_serving": snapshot["total_serving"],
            "active_counters": snapshot["active_counters"],
            "total_counters": snapshot["total_counters"],
            "is_stalled": snapshot["is_stalled"],
        },
    }


async def tool_get_service_details(
    session: AsyncSession,
    service_code: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Get detailed metrics for a specific service category.
    """
    cat_stmt = select(ServiceCategory).where(ServiceCategory.code == service_code.upper())
    cat_res = await session.execute(cat_stmt)
    cat = cat_res.scalar_one_or_none()

    if not cat:
        return {"error": f"Service code '{service_code}' not found"}

    token_stmt = select(Token).where(
        Token.simulation_run_id.is_(None),
        Token.session_id == session_id,
        Token.service_category_id == cat.id,
    )
    token_res = await session.execute(token_stmt)
    tokens = list(token_res.scalars().all())

    waiting = [t for t in tokens if t.status == TokenStatus.WAITING]
    completed = [t for t in tokens if t.status == TokenStatus.COMPLETED]
    skipped = [t for t in tokens if t.status == TokenStatus.SKIPPED]

    wait_times = []
    service_durations = []
    for t in tokens:
        if t.called_at and t.created_at:
            wait_times.append((t.called_at - t.created_at).total_seconds())
        if t.status == TokenStatus.COMPLETED and t.completed_at and t.service_started_at:
            service_durations.append((t.completed_at - t.service_started_at).total_seconds())

    return {
        "service_code": cat.code,
        "service_name": cat.name,
        "default_duration_seconds": cat.default_duration_seconds,
        "total_issued": len(tokens),
        "currently_waiting": len(waiting),
        "completed": len(completed),
        "skipped": len(skipped),
        "avg_wait_seconds": round(sum(wait_times) / len(wait_times)) if wait_times else 0,
        "max_wait_seconds": round(max(wait_times)) if wait_times else 0,
        "avg_service_seconds": round(sum(service_durations) / len(service_durations)) if service_durations else cat.default_duration_seconds,
        "no_show_rate_pct": round((len(skipped) / max(1, len(tokens))) * 100, 1),
    }
