"""
QueueWise AI — Model Context Protocol (MCP) Tool Server

Implements the standard Model Context Protocol (MCP) for exposing QueueWise AI
operations tools to external AI agents and desktop clients (Claude Desktop, Antigravity, Cursor).

Supports:
- JSON-RPC 2.0 specification (initialize, tools/list, tools/call, ping)
- Read-only and operational queue tools
- Direct database execution with session management
- Strict JSON Schema validation
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.token import Token, TokenStatus
from app.models.counter import Counter, CounterStatus
from app.models.service_category import ServiceCategory
from app.services.queue_engine import QueueEngine
from app.services.wait_estimator import WaitEstimator
from app.services.analytics_service import AnalyticsService


# --- MCP Tool Schemas ---

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_queue_status",
        "description": "Get real-time queue snapshot including waiting tokens, serving tokens, active counters, and per-service breakdown.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Queue session ID to query",
                    "default": "default",
                },
            },
        },
    },
    {
        "name": "get_wait_estimate",
        "description": "Calculate dynamic wait-time estimate for a specific service or an existing token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_code": {
                    "type": "string",
                    "description": "Service code (e.g. GEN, DOC, CASH)",
                },
                "token_public_id": {
                    "type": "string",
                    "description": "Public ID of an existing token to check position and estimate",
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                },
            },
        },
    },
    {
        "name": "get_analytics_summary",
        "description": "Retrieve operational performance KPIs, including SLA compliance %, completion rate, average wait time, and counter utilization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "integer",
                    "description": "Time window in hours (default 24)",
                    "default": 24,
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                },
            },
        },
    },
    {
        "name": "get_optimization_recommendation",
        "description": "Generate algorithmic counter reallocation recommendations using multi-server M/M/c queue theory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "default": "default",
                },
            },
        },
    },
    {
        "name": "list_services",
        "description": "List all active public service categories with their default durations and SLA thresholds.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "issue_citizen_token",
        "description": "Issue a new digital queue token for a citizen requesting service.",
        "inputSchema": {
            "type": "object",
            "required": ["service_code"],
            "properties": {
                "service_code": {
                    "type": "string",
                    "description": "Service category code (e.g. GEN, DOC, CASH)",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority score (0 = regular, 5 = senior citizen / emergency assistance)",
                    "default": 0,
                },
                "contact_info": {
                    "type": "string",
                    "description": "Optional mobile number or contact identifier",
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                },
            },
        },
    },
    {
        "name": "call_next_token",
        "description": "Operator action: Call the next highest-priority waiting token to a physical counter desk.",
        "inputSchema": {
            "type": "object",
            "required": ["counter_id"],
            "properties": {
                "counter_id": {
                    "type": "string",
                    "description": "UUID string of the counter desk calling next",
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                },
            },
        },
    },
]


class MCPServer:
    """Model Context Protocol handler for QueueWise AI operations."""

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Return the list of tool definitions conforming to the MCP spec."""
        return MCP_TOOLS

    @classmethod
    async def invoke_tool(
        cls,
        session: AsyncSession,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool by name with arguments against the live database.
        Returns standard MCP content response structure.
        """
        args = arguments or {}
        session_id = args.get("session_id", "default")

        try:
            if tool_name == "get_queue_status":
                result = await cls._tool_queue_status(session, session_id)
            elif tool_name == "get_wait_estimate":
                result = await cls._tool_wait_estimate(session, args)
            elif tool_name == "get_analytics_summary":
                result = await cls._tool_analytics_summary(session, args)
            elif tool_name == "get_optimization_recommendation":
                result = await cls._tool_optimization_recommendation(session, session_id)
            elif tool_name == "list_services":
                result = await cls._tool_list_services(session)
            elif tool_name == "issue_citizen_token":
                result = await cls._tool_issue_token(session, args)
            elif tool_name == "call_next_token":
                result = await cls._tool_call_next(session, args)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: '{tool_name}'"}],
                    "isError": True,
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str),
                    }
                ],
                "isError": False,
            }

        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error executing {tool_name}: {str(e)}"}],
                "isError": True,
            }

    # --- Tool Implementations ---

    @classmethod
    async def _tool_queue_status(
        cls, session: AsyncSession, session_id: str
    ) -> Dict[str, Any]:
        services_stmt = select(ServiceCategory).where(ServiceCategory.is_active == True)
        services_res = await session.execute(services_stmt)
        services = services_res.scalars().all()

        service_breakdown = []
        total_waiting = 0

        for s in services:
            count_stmt = select(func.count(Token.id)).where(
                and_(
                    Token.service_category_id == s.id,
                    Token.session_id == session_id,
                    Token.status == TokenStatus.WAITING,
                )
            )
            count = (await session.execute(count_stmt)).scalar() or 0
            total_waiting += count
            service_breakdown.append({
                "code": s.code,
                "name": s.name,
                "waiting_count": count,
            })

        counters_stmt = select(Counter)
        counters = (await session.execute(counters_stmt)).scalars().all()
        active_counters = sum(1 for c in counters if c.status in (CounterStatus.OPEN_IDLE, CounterStatus.OPEN_SERVING))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "total_waiting": total_waiting,
            "active_counters": active_counters,
            "total_counters": len(counters),
            "services": service_breakdown,
        }

    @classmethod
    async def _tool_wait_estimate(
        cls, session: AsyncSession, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        session_id = args.get("session_id", "default")
        token_public_id = args.get("token_public_id")
        service_code = args.get("service_code")

        if token_public_id:
            token = await QueueEngine.get_token_by_public_id(session, token_public_id)
            estimate = await WaitEstimator.estimate_token_wait(session, token)
            pos, ahead = await QueueEngine.get_queue_position_and_ahead(session, token)
            return {
                "display_number": token.display_number,
                "status": token.status.value,
                "position": pos,
                "people_ahead": ahead,
                "estimated_wait_seconds": estimate.get("estimated_wait_seconds", 0),
                "estimated_wait_minutes": estimate.get("estimated_wait_minutes", 0.0),
                "active_counters": estimate.get("active_counters", 0),
            }

        if service_code:
            svc_stmt = select(ServiceCategory).where(ServiceCategory.code == service_code.upper())
            service = (await session.execute(svc_stmt)).scalar_one_or_none()
            if not service:
                raise ValueError(f"Service category with code '{service_code}' not found")
            estimate = await WaitEstimator.estimate_prospective_arrival(
                session, service.id, session_id=session_id
            )
            return {
                "service_code": service.code,
                "service_name": service.name,
                "estimated_wait_seconds": estimate.estimated_wait_seconds,
                "estimated_wait_minutes": estimate.estimated_wait_minutes,
                "waiting_ahead": estimate.position_ahead,
                "active_counters": estimate.active_counters,
            }

        raise ValueError("Must provide either 'service_code' or 'token_public_id'")

    @classmethod
    async def _tool_analytics_summary(
        cls, session: AsyncSession, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        hours_back = args.get("hours_back", 24)
        session_id = args.get("session_id", "default")
        start_time = None
        if hours_back and hours_back > 0:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        summary = await AnalyticsService.get_summary_metrics(
            session=session,
            start_time=start_time,
            session_id=session_id,
        )
        return summary.model_dump()

    @classmethod
    async def _tool_optimization_recommendation(
        cls, session: AsyncSession, session_id: str
    ) -> Dict[str, Any]:
        from app.agents.tools import tool_get_optimization_recommendation
        return await tool_get_optimization_recommendation(session, session_id=session_id)

    @classmethod
    async def _tool_list_services(cls, session: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(ServiceCategory).where(ServiceCategory.is_active == True)
        services = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "description": s.description,
                "default_duration_seconds": s.default_duration_seconds,
                "priority_policy": s.priority_policy,
            }
            for s in services
        ]

    @classmethod
    async def _tool_issue_token(
        cls, session: AsyncSession, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        service_code = args.get("service_code")
        if not service_code:
            raise ValueError("service_code is required")
        priority = args.get("priority", 0)
        contact_info = args.get("contact_info")
        session_id = args.get("session_id", "default")

        token = await QueueEngine.create_token(
            session=session,
            service_code=service_code,
            priority=priority,
            contact_info=contact_info,
            session_id=session_id,
        )
        pos, ahead = await QueueEngine.get_queue_position_and_ahead(session, token)
        estimate = await WaitEstimator.estimate_token_wait(session, token)

        return {
            "token_id": str(token.id),
            "public_id": token.public_id,
            "display_number": token.display_number,
            "service_code": service_code.upper(),
            "priority": token.priority,
            "position": pos,
            "people_ahead": ahead,
            "estimated_wait_seconds": estimate.get("estimated_wait_seconds", 0),
            "status": token.status.value,
        }

    @classmethod
    async def _tool_call_next(
        cls, session: AsyncSession, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        counter_id_str = args.get("counter_id")
        if not counter_id_str:
            raise ValueError("counter_id is required")
        import uuid
        counter_uuid = uuid.UUID(counter_id_str)
        session_id = args.get("session_id", "default")

        token = await QueueEngine.call_next_token(
            session=session,
            counter_id=counter_uuid,
            session_id=session_id,
        )

        if not token:
            return {
                "called": False,
                "message": "No tokens currently waiting for this counter's assigned services.",
            }

        return {
            "called": True,
            "token_id": str(token.id),
            "display_number": token.display_number,
            "public_id": token.public_id,
            "status": token.status.value,
            "called_counter_id": counter_id_str,
        }

    # --- JSON-RPC 2.0 Dispatcher ---

    @classmethod
    async def handle_jsonrpc(
        cls, session: AsyncSession, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle standard MCP JSON-RPC 2.0 request.
        """
        msg_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "QueueWise-AI-MCP-Server",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                },
            }

        elif method == "notifications/initialized":
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": cls.get_tool_definitions()},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Missing 'name' parameter"},
                }

            exec_result = await cls.invoke_tool(session, tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": exec_result,
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found",
                },
            }
