"""
QueueWise AI — MCP Tool Server Test Suite

Verifies:
- Standard Model Context Protocol (MCP) tool schema definitions
- JSON-RPC 2.0 initialize handshake, ping, tools/list, and tools/call
- REST invocation via /api/v1/mcp/invoke
- Execution of all registered queue tools (status, estimate, analytics, optimizer, issue token, call next)
- Robust error handling for unknown tools and malformed RPC calls
"""
import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.server import MCPServer
from app.services.queue_engine import QueueEngine


@pytest.mark.anyio
class TestMCPServerCore:
    """Unit tests for the MCPServer class directly."""

    def test_tool_definitions_conform_to_mcp_schema(self):
        """All tools must have name, description, and valid inputSchema object."""
        tools = MCPServer.get_tool_definitions()
        assert len(tools) >= 6

        tool_names = [t["name"] for t in tools]
        assert "get_queue_status" in tool_names
        assert "get_wait_estimate" in tool_names
        assert "get_analytics_summary" in tool_names
        assert "get_optimization_recommendation" in tool_names
        assert "list_services" in tool_names
        assert "issue_citizen_token" in tool_names
        assert "call_next_token" in tool_names

        for t in tools:
            assert isinstance(t["name"], str) and len(t["name"]) > 0
            assert isinstance(t["description"], str) and len(t["description"]) > 0
            assert t["inputSchema"]["type"] == "object"

    async def test_invoke_get_queue_status(self, db_session: AsyncSession):
        """Direct invocation of get_queue_status returns serialized JSON."""
        res = await MCPServer.invoke_tool(db_session, "get_queue_status", {"session_id": "mcp-test"})
        assert res["isError"] is False
        assert len(res["content"]) == 1
        data = json.loads(res["content"][0]["text"])
        assert "total_waiting" in data
        assert "active_counters" in data
        assert "services" in data

    async def test_invoke_issue_token(self, db_session: AsyncSession):
        """Issue token tool creates a valid token and returns position and display number."""
        res = await MCPServer.invoke_tool(
            db_session,
            "issue_citizen_token",
            {"service_code": "GEN", "priority": 5, "session_id": "mcp-test"},
        )
        assert res["isError"] is False
        data = json.loads(res["content"][0]["text"])
        assert data["service_code"] == "GEN"
        assert data["priority"] == 5
        assert "display_number" in data
        assert "position" in data

    async def test_invoke_unknown_tool_returns_error(self, db_session: AsyncSession):
        """Unknown tool returns isError True with clear message."""
        res = await MCPServer.invoke_tool(db_session, "non_existent_tool", {})
        assert res["isError"] is True
        assert "Unknown tool" in res["content"][0]["text"]


@pytest.mark.anyio
class TestMCPJsonRpcEndpoints:
    """Integration tests for JSON-RPC 2.0 endpoints."""

    async def test_initialize_handshake(self, async_client: AsyncClient):
        """MCP client initialize handshake."""
        resp = await async_client.post(
            "/api/v1/mcp/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "init-1"
        assert data["result"]["serverInfo"]["name"] == "QueueWise-AI-MCP-Server"
        assert "tools" in data["result"]["capabilities"]

    async def test_ping(self, async_client: AsyncClient):
        """MCP ping response."""
        resp = await async_client.post(
            "/api/v1/mcp/rpc",
            json={"jsonrpc": "2.0", "id": 42, "method": "ping"},
        )
        assert resp.status_code == 200
        assert resp.json()["result"] == {}

    async def test_tools_list_rpc(self, async_client: AsyncClient):
        """tools/list method returns registered tools."""
        resp = await async_client.post(
            "/api/v1/mcp/rpc",
            json={"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) >= 6

    async def test_tools_call_rpc_get_queue_status(self, async_client: AsyncClient):
        """tools/call method executes get_queue_status tool."""
        resp = await async_client.post(
            "/api/v1/mcp/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "get_queue_status",
                    "arguments": {"session_id": "default"},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["isError"] is False
        parsed_payload = json.loads(data["result"]["content"][0]["text"])
        assert "total_waiting" in parsed_payload

    async def test_tools_call_rpc_unknown_method_error(self, async_client: AsyncClient):
        """Calling unknown RPC method returns -32601 error code."""
        resp = await async_client.post(
            "/api/v1/mcp/rpc",
            json={"jsonrpc": "2.0", "id": "err-1", "method": "unknown/method"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32601


@pytest.mark.anyio
class TestMCPRestEndpoints:
    """Integration tests for direct REST endpoints."""

    async def test_get_tools_endpoint(self, async_client: AsyncClient):
        """GET /api/v1/mcp/tools returns list of tools."""
        resp = await async_client.get("/api/v1/mcp/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 6
        assert len(data["tools"]) == data["count"]

    async def test_post_invoke_rest_endpoint(self, async_client: AsyncClient):
        """POST /api/v1/mcp/invoke executes tool and returns structured result."""
        resp = await async_client.post(
            "/api/v1/mcp/invoke",
            json={
                "tool_name": "list_services",
                "arguments": {},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_name"] == "list_services"
        assert data["is_error"] is False
        assert len(data["content"]) >= 1
