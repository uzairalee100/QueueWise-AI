"""
QueueWise AI — MCP API Endpoints

Provides REST and JSON-RPC 2.0 endpoints for the Model Context Protocol (MCP) server:
- GET  /api/v1/mcp/tools  -> Discover registered tools
- POST /api/v1/mcp/invoke -> Direct REST tool execution
- POST /api/v1/mcp/rpc    -> Standard MCP JSON-RPC 2.0 transport
- POST /api/v1/mcp        -> Standard MCP JSON-RPC 2.0 alias
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.mcp.server import MCPServer
from app.schemas.mcp import (
    MCPToolInvokeRequest,
    MCPToolInvokeResponse,
    MCPToolContent,
    MCPJsonRpcRequest,
    MCPJsonRpcResponse,
)

router = APIRouter()


@router.get(
    "/tools",
    summary="List MCP Tools",
    description="Discover all registered tools conforming to Model Context Protocol specification.",
)
async def list_tools() -> Dict[str, Any]:
    """Return all available MCP tools and their JSON schemas."""
    return {
        "tools": MCPServer.get_tool_definitions(),
        "count": len(MCPServer.get_tool_definitions()),
    }


@router.post(
    "/invoke",
    response_model=MCPToolInvokeResponse,
    summary="Invoke MCP Tool (REST)",
    description="Directly execute an MCP tool with name and argument payload.",
)
async def invoke_tool(
    request: MCPToolInvokeRequest,
    session: AsyncSession = Depends(get_db),
) -> MCPToolInvokeResponse:
    """Execute a tool directly via REST."""
    result = await MCPServer.invoke_tool(
        session=session,
        tool_name=request.tool_name,
        arguments=request.arguments,
    )
    return MCPToolInvokeResponse(
        tool_name=request.tool_name,
        content=[MCPToolContent(**item) for item in result.get("content", [])],
        is_error=result.get("isError", False),
    )


@router.post(
    "/rpc",
    response_model=MCPJsonRpcResponse,
    summary="MCP JSON-RPC 2.0 Endpoint",
    description="Standard Model Context Protocol JSON-RPC 2.0 transport (tools/list, tools/call, initialize).",
)
@router.post(
    "",
    response_model=MCPJsonRpcResponse,
    summary="MCP JSON-RPC 2.0 Root Endpoint",
)
async def handle_mcp_rpc(
    rpc_request: MCPJsonRpcRequest,
    session: AsyncSession = Depends(get_db),
) -> MCPJsonRpcResponse:
    """Handle standard JSON-RPC 2.0 request."""
    response_dict = await MCPServer.handle_jsonrpc(
        session=session,
        payload=rpc_request.model_dump(),
    )
    return MCPJsonRpcResponse(**response_dict)
