"""
QueueWise AI — MCP Pydantic Schemas

Schemas for JSON-RPC 2.0 and REST-based MCP operations.
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class MCPToolInvokeRequest(BaseModel):
    """Request body for direct REST tool invocation."""
    tool_name: str = Field(..., description="Name of the MCP tool to invoke")
    arguments: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )


class MCPToolContent(BaseModel):
    """Single content item in MCP response."""
    type: str = Field(default="text", description="Content type (e.g. text)")
    text: str = Field(description="Payload text content (often serialized JSON)")


class MCPToolInvokeResponse(BaseModel):
    """Standard MCP tool invocation result."""
    tool_name: str = Field(description="Name of the invoked tool")
    content: List[MCPToolContent] = Field(description="List of content chunks")
    is_error: bool = Field(default=False, description="Whether execution resulted in an error")


class MCPJsonRpcRequest(BaseModel):
    """Standard JSON-RPC 2.0 request payload."""
    jsonrpc: str = Field(default="2.0", description="Protocol version")
    id: Optional[Union[str, int]] = Field(default=None, description="Message identifier")
    method: str = Field(..., description="Method name, e.g. tools/list, tools/call")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")


class MCPJsonRpcResponse(BaseModel):
    """Standard JSON-RPC 2.0 response payload."""
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
