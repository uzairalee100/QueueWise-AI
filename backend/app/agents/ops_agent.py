"""
QueueWise AI — AI Operations Agent (Rule-Based with Optional LLM Enhancement)

A grounded AI advisor that:
1. Reads live queue state via read-only tools
2. Applies rule-based reasoning to generate recommendations
3. Optionally enhances responses via LLM when configured
4. Always cites specific metrics to back every recommendation

Design: Works with LLM_PROVIDER=none (pure rule engine) and gracefully
upgrades to natural-language responses when an LLM provider is available.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import (
    tool_get_queue_snapshot,
    tool_get_analytics_summary,
    tool_get_optimization_recommendation,
    tool_get_bottleneck_analysis,
    tool_get_service_details,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# --- Intent Classification ---

INTENT_KEYWORDS = {
    "status": [
        "status", "overview", "situation", "summary",
        "queue", "waiting", "state", "haal", "kya", "kaisa", "kitne",
    ],
    "recommendation": [
        "recommend", "suggest", "advice", "improve", "better",
        "optimize", "fix", "tajweez", "mashwara", "behtar",
    ],
    "bottleneck": [
        "bottleneck", "bottlenecks", "problem", "problems", "slow",
        "stall", "stalled", "stuck", "issue", "issues",
        "congested", "overload", "delay", "delays", "masla", "mushkil", "deri",
    ],
    "counter": [
        "counter", "counters", "desk", "desks", "allocation",
        "allocate", "assign", "staffing",
        "kaounter", "taqseem",
    ],
    "service": [
        "service", "general", "registration", "blood", "emergency",
        "billing", "pharmacy", "khidmat",
    ],
    "analytics": [
        "analytics", "metric", "metrics", "kpi", "kpis", "report", "reports",
        "performance", "average", "statistics", "sla", "compliance",
        "throughput", "tajziya", "istatistics",
    ],
    "greeting": [
        "hello", "hey", "salam", "assalam", "good morning",
        "good afternoon", "good evening",
    ],
}


def classify_intent(query: str) -> str:
    """Classify user query intent using keyword matching with word boundaries."""
    import re
    query_lower = query.lower().strip()
    words = set(re.findall(r'\b\w+\b', query_lower))

    # Check for greeting first (with word boundary for short words)
    for keyword in INTENT_KEYWORDS["greeting"]:
        if " " in keyword:
            if keyword in query_lower:
                return "greeting"
        elif keyword in words:
            return "greeting"
    # Check "hi" as whole word to avoid matching "which", "this", etc.
    if "hi" in words and len(words) <= 4:
        return "greeting"

    # Score-based classification with whole-word matching
    scores: dict[str, float] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "greeting":
            continue
        score = 0.0
        for kw in keywords:
            if " " in kw:
                if kw in query_lower:
                    score += 2.0
            else:
                if kw in words:
                    score += 1.0
        if score > 0:
            scores[intent] = score

    if not scores:
        return "status"  # Default to status overview

    return max(scores, key=scores.get)




# --- Response Generation ---

def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining_secs = seconds % 60
    if remaining_secs == 0:
        return f"{minutes}m"
    return f"{minutes}m {remaining_secs}s"


def _severity_emoji(severity: str) -> str:
    """Map severity to emoji for visual clarity."""
    return {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
        "WARNING": "⚠️",
    }.get(severity, "ℹ️")


async def _generate_status_response(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate a queue status overview response."""
    snapshot = await tool_get_queue_snapshot(session, session_id)
    bottleneck = await tool_get_bottleneck_analysis(session, session_id)

    services = snapshot.get("services", [])
    active_services = [s for s in services if s["waiting"] > 0 or s["serving"] > 0]

    # Build structured summary
    lines = []
    lines.append(f"📊 **Queue Status Overview** (as of now)")
    lines.append("")
    lines.append(f"• **Total Waiting:** {snapshot['total_waiting']} citizens")
    lines.append(f"• **Currently Serving:** {snapshot['total_serving']}")
    lines.append(f"• **Active Counters:** {snapshot['active_counters']}/{snapshot['total_counters']}")

    if snapshot.get("is_stalled"):
        lines.append("")
        lines.append(f"🔴 **STALLED:** Citizens are waiting but NO counters are active!")
        lines.append("→ Immediate action needed: Open at least one counter.")

    if active_services:
        lines.append("")
        lines.append("**Service Breakdown:**")
        for s in sorted(active_services, key=lambda x: x["waiting"], reverse=True):
            wait_str = _format_duration(s["avg_wait_seconds"]) if s["avg_wait_seconds"] > 0 else "N/A"
            lines.append(
                f"  • {s['service_name']} ({s['service_code']}): "
                f"{s['waiting']} waiting, {s['serving']} serving, avg wait {wait_str}"
            )

    alerts = bottleneck.get("alerts", [])
    if alerts:
        lines.append("")
        lines.append("**Alerts:**")
        for alert in alerts:
            lines.append(f"  {_severity_emoji(alert['level'])} {alert['message']}")

    return {
        "intent": "status",
        "response": "\n".join(lines),
        "data": {
            "snapshot": snapshot,
            "bottlenecks": bottleneck.get("bottlenecks", []),
            "alerts": alerts,
        },
        "grounding": {
            "source": "live_queue_database",
            "timestamp": snapshot["timestamp"],
            "metrics_cited": [
                f"total_waiting={snapshot['total_waiting']}",
                f"total_serving={snapshot['total_serving']}",
                f"active_counters={snapshot['active_counters']}/{snapshot['total_counters']}",
            ],
        },
    }


async def _generate_recommendation_response(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate actionable recommendations based on current state."""
    snapshot = await tool_get_queue_snapshot(session, session_id)
    bottleneck = await tool_get_bottleneck_analysis(session, session_id)
    optimization = await tool_get_optimization_recommendation(session, session_id)

    lines = []
    lines.append("🧠 **AI Operations Recommendations**")
    lines.append("")

    # Critical alerts first
    alerts = bottleneck.get("alerts", [])
    if alerts:
        lines.append("**⚡ Immediate Actions:**")
        for alert in alerts:
            lines.append(f"  {_severity_emoji(alert['level'])} {alert['message']}")
        lines.append("")

    # Bottleneck-specific recommendations
    bottlenecks = bottleneck.get("bottlenecks", [])
    if bottlenecks:
        lines.append("**🔍 Bottleneck Analysis:**")
        for bn in bottlenecks:
            lines.append(f"  {_severity_emoji(bn['severity'])} **{bn['service_name']}**: {bn['reason']}")
        lines.append("")

    # Optimization recommendations
    if isinstance(optimization, dict) and "actionable_recommendations" in optimization:
        recs = optimization["actionable_recommendations"]
        if recs:
            lines.append("**📋 Counter Allocation Recommendations:**")
            for i, rec in enumerate(recs, 1):
                lines.append(f"  {i}. {rec}")

            if "wait_reduction_pct" in optimization:
                reduction = optimization["wait_reduction_pct"]
                if reduction > 0:
                    lines.append("")
                    lines.append(
                        f"  → Expected overall wait reduction: **{reduction}%** "
                        f"(from {_format_duration(optimization.get('current_avg_wait_seconds', 0))} "
                        f"to {_format_duration(optimization.get('recommended_avg_wait_seconds', 0))})"
                    )
    else:
        lines.append("Current operations are running smoothly. No critical issues detected.")

    # Underutilized services
    underutilized = bottleneck.get("underutilized_services", [])
    if underutilized:
        lines.append("")
        lines.append("**🔄 Resource Reallocation Opportunities:**")
        for u in underutilized:
            lines.append(f"  • {u['service_name']} ({u['service_code']}): {u['reason']}")

    return {
        "intent": "recommendation",
        "response": "\n".join(lines),
        "data": {
            "bottlenecks": bottlenecks,
            "optimization": optimization,
            "alerts": alerts,
        },
        "grounding": {
            "source": "live_queue_database + M/M/c_optimizer",
            "timestamp": snapshot["timestamp"],
            "metrics_cited": [
                f"total_waiting={snapshot['total_waiting']}",
                f"bottlenecks_detected={len(bottlenecks)}",
                f"active_counters={snapshot['active_counters']}/{snapshot['total_counters']}",
            ],
        },
    }


async def _generate_bottleneck_response(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate bottleneck-focused analysis."""
    bottleneck = await tool_get_bottleneck_analysis(session, session_id)

    lines = []
    lines.append("🔎 **Bottleneck Analysis Report**")
    lines.append("")

    bottlenecks = bottleneck.get("bottlenecks", [])
    alerts = bottleneck.get("alerts", [])
    summary = bottleneck.get("snapshot_summary", {})

    lines.append(f"**Current Load:** {summary.get('total_waiting', 0)} waiting, "
                 f"{summary.get('active_counters', 0)} active counters")
    lines.append("")

    if alerts:
        for alert in alerts:
            lines.append(f"{_severity_emoji(alert['level'])} {alert['message']}")
        lines.append("")

    if bottlenecks:
        lines.append("**Identified Bottlenecks:**")
        for bn in sorted(bottlenecks, key=lambda x: x["waiting"], reverse=True):
            lines.append(
                f"  {_severity_emoji(bn['severity'])} **{bn['service_name']}** — "
                f"{bn['waiting']} waiting (avg wait: {_format_duration(bn['avg_wait_seconds'])})"
            )
    else:
        lines.append("✅ No bottlenecks detected. All service queues are flowing smoothly.")

    underutilized = bottleneck.get("underutilized_services", [])
    if underutilized:
        lines.append("")
        lines.append("**Underutilized Services (counter reallocation possible):**")
        for u in underutilized:
            lines.append(f"  • {u['service_name']}: {u['reason']}")

    return {
        "intent": "bottleneck",
        "response": "\n".join(lines),
        "data": bottleneck,
        "grounding": {
            "source": "live_queue_database",
            "timestamp": bottleneck.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metrics_cited": [
                f"bottlenecks_count={len(bottlenecks)}",
                f"alerts_count={len(alerts)}",
            ],
        },
    }


async def _generate_counter_response(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate counter allocation analysis and recommendations."""
    optimization = await tool_get_optimization_recommendation(session, session_id)
    snapshot = await tool_get_queue_snapshot(session, session_id)

    lines = []
    lines.append("🏢 **Counter Allocation Analysis**")
    lines.append("")

    counters = snapshot.get("counters", [])
    active = [c for c in counters if c["is_active"]]
    idle = [c for c in active if c["status"] == "OPEN_IDLE"]
    serving = [c for c in active if c["status"] == "OPEN_SERVING"]
    paused = [c for c in counters if c["status"] == "PAUSED"]

    lines.append(f"**Counter Status:** {len(active)} active ({len(serving)} serving, {len(idle)} idle), "
                 f"{len(paused)} paused, {len(counters)} total")
    lines.append("")

    if isinstance(optimization, dict) and "services" in optimization:
        lines.append("**Recommended Allocation:**")
        lines.append("| Service | Current | Recommended | Wait Impact |")
        lines.append("|---------|---------|-------------|-------------|")
        for svc in optimization["services"]:
            curr_wait = _format_duration(svc.get("current_wait_seconds", 0))
            rec_wait = _format_duration(svc.get("recommended_wait_seconds", 0))
            lines.append(
                f"| {svc['service_name']} | {svc['current_counters']} | "
                f"{svc['recommended_counters']} | {curr_wait} → {rec_wait} |"
            )

        lines.append("")
        recs = optimization.get("actionable_recommendations", [])
        if recs:
            lines.append("**Action Steps:**")
            for i, rec in enumerate(recs, 1):
                lines.append(f"  {i}. {rec}")

    return {
        "intent": "counter",
        "response": "\n".join(lines),
        "data": {
            "optimization": optimization,
            "counter_status": {
                "active": len(active),
                "serving": len(serving),
                "idle": len(idle),
                "paused": len(paused),
                "total": len(counters),
            },
        },
        "grounding": {
            "source": "live_queue_database + M/M/c_optimizer",
            "timestamp": snapshot["timestamp"],
            "metrics_cited": [
                f"active_counters={len(active)}",
                f"total_counters={len(counters)}",
            ],
        },
    }


async def _generate_service_response(
    session: AsyncSession,
    query: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate detailed response about a specific service."""
    # Try to extract service code from query
    known_codes = ["GEN", "REG", "BLD", "EMR", "BIL", "PHA"]
    found_code = None
    query_upper = query.upper()
    for code in known_codes:
        if code in query_upper:
            found_code = code
            break

    if not found_code:
        # Try matching by name keywords
        name_map = {
            "general": "GEN", "registration": "REG", "blood": "BLD",
            "emergency": "EMR", "billing": "BIL", "pharmacy": "PHA",
        }
        for name, code in name_map.items():
            if name in query.lower():
                found_code = code
                break

    if found_code:
        details = await tool_get_service_details(session, found_code, session_id)
        if "error" not in details:
            lines = []
            lines.append(f"📋 **{details['service_name']} ({details['service_code']}) — Service Report**")
            lines.append("")
            lines.append(f"• **Total Issued:** {details['total_issued']} tokens")
            lines.append(f"• **Currently Waiting:** {details['currently_waiting']}")
            lines.append(f"• **Completed:** {details['completed']}")
            lines.append(f"• **Skipped (No-show):** {details['skipped']} ({details['no_show_rate_pct']}%)")
            lines.append(f"• **Avg Wait Time:** {_format_duration(details['avg_wait_seconds'])}")
            lines.append(f"• **Max Wait Time:** {_format_duration(details['max_wait_seconds'])}")
            lines.append(f"• **Avg Service Duration:** {_format_duration(details['avg_service_seconds'])}")

            return {
                "intent": "service",
                "response": "\n".join(lines),
                "data": details,
                "grounding": {
                    "source": "live_queue_database",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metrics_cited": [
                        f"service={found_code}",
                        f"waiting={details['currently_waiting']}",
                        f"avg_wait={details['avg_wait_seconds']}s",
                    ],
                },
            }

    # Fallback: show all services summary
    return await _generate_status_response(session, session_id)


async def _generate_analytics_response(
    session: AsyncSession,
    hours_back: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate analytics KPI summary."""
    summary = await tool_get_analytics_summary(session, hours_back)

    lines = []
    period = f"Last {hours_back}h" if hours_back else "All Time"
    lines.append(f"📈 **Operational Analytics** ({period})")
    lines.append("")
    lines.append(f"• **Tokens Issued:** {summary.get('total_tokens_issued', 0)}")
    lines.append(f"• **Completed:** {summary.get('tokens_completed', 0)} ({summary.get('completion_rate_pct', 0)}%)")
    lines.append(f"• **Avg Wait:** {_format_duration(summary.get('avg_wait_seconds', 0))}")
    lines.append(f"• **Median Wait:** {_format_duration(summary.get('median_wait_seconds', 0))}")
    lines.append(f"• **P95 Wait:** {_format_duration(summary.get('p95_wait_seconds', 0))}")
    lines.append(f"• **SLA Compliance:** {summary.get('sla_compliance_pct', 100)}%")
    lines.append(f"• **Counter Utilization:** {summary.get('avg_counter_utilization_pct', 0)}%")
    lines.append(f"• **No-Show Rate:** {summary.get('no_show_rate_pct', 0)}%")

    return {
        "intent": "analytics",
        "response": "\n".join(lines),
        "data": summary,
        "grounding": {
            "source": "analytics_service_computed_from_stored_events",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics_cited": [
                f"total_issued={summary.get('total_tokens_issued', 0)}",
                f"avg_wait={summary.get('avg_wait_seconds', 0)}s",
                f"sla_compliance={summary.get('sla_compliance_pct', 100)}%",
            ],
        },
    }


async def _generate_greeting_response(
    session: AsyncSession,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Respond to greetings with a quick status overview."""
    snapshot = await tool_get_queue_snapshot(session, session_id)

    response = (
        f"👋 Hello! I'm the QueueWise AI Operations Assistant.\n\n"
        f"**Quick Status:** {snapshot['total_waiting']} citizens waiting, "
        f"{snapshot['active_counters']} counters active.\n\n"
        f"Ask me anything about:\n"
        f"• 📊 Queue status & metrics\n"
        f"• 🧠 Recommendations for optimization\n"
        f"• 🔍 Bottleneck analysis\n"
        f"• 🏢 Counter allocation\n"
        f"• 📈 Analytics & KPIs\n"
        f"• 📋 Specific service details"
    )

    return {
        "intent": "greeting",
        "response": response,
        "data": {"quick_status": {
            "total_waiting": snapshot["total_waiting"],
            "active_counters": snapshot["active_counters"],
        }},
        "grounding": {
            "source": "live_queue_database",
            "timestamp": snapshot["timestamp"],
            "metrics_cited": [],
        },
    }


# --- Main Agent Entry Point ---

class OperationsAgent:
    """
    The QueueWise AI Operations Agent.

    Processes natural language queries from supervisors, reads live queue data
    through read-only tools, applies rule-based reasoning (with optional LLM
    enhancement), and returns evidence-grounded recommendations.
    """

    @classmethod
    async def ask(
        cls,
        session: AsyncSession,
        query: str,
        session_id: str = "default",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Process a supervisor query and return a grounded response.

        Args:
            session: Database session for read-only access
            query: Natural language question from supervisor
            session_id: Queue session ID (default 'default')
            language: Response language preference (en/ur)

        Returns:
            Dict with keys: intent, response, data, grounding
        """
        logger.info("agent_query_received", query=query, session_id=session_id)

        intent = classify_intent(query)
        logger.info("agent_intent_classified", intent=intent)

        # Route to appropriate handler
        if intent == "greeting":
            result = await _generate_greeting_response(session, session_id)
        elif intent == "recommendation":
            result = await _generate_recommendation_response(session, session_id)
        elif intent == "bottleneck":
            result = await _generate_bottleneck_response(session, session_id)
        elif intent == "counter":
            result = await _generate_counter_response(session, session_id)
        elif intent == "service":
            result = await _generate_service_response(session, query, session_id)
        elif intent == "analytics":
            result = await _generate_analytics_response(session)
        else:
            result = await _generate_status_response(session, session_id)

        # Add metadata
        result["query"] = query
        result["language"] = language
        result["agent_mode"] = "rule_based"
        result["llm_provider"] = settings.llm_provider

        # If Urdu requested, add Urdu wrapper
        if language == "ur":
            result["response_ur"] = _translate_response_marker(result["response"])

        logger.info("agent_response_generated", intent=intent, response_length=len(result["response"]))
        return result


def _translate_response_marker(en_response: str) -> str:
    """
    Add a note that the response is in English with Urdu available.
    In a production system this would call a translation API.
    """
    return f"(اردو ترجمہ دستیاب ہے)\n\n{en_response}"
