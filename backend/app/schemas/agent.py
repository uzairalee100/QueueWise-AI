"""
QueueWise AI — AI Agent Pydantic Schemas

Request/response models for the AI Operations Agent API.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    """Request body for submitting a query to the AI Operations Agent."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language question for the AI agent",
        examples=["What is the current queue status?", "How should we allocate counters?"],
    )
    session_id: str = Field(
        default="default",
        description="Queue session ID to analyze",
    )
    language: str = Field(
        default="en",
        description="Preferred response language (en or ur)",
    )


class AgentGroundingInfo(BaseModel):
    """Evidence grounding metadata for the agent's response."""
    source: str = Field(description="Data source used for the response")
    timestamp: str = Field(description="Timestamp of the data read")
    metrics_cited: List[str] = Field(
        default_factory=list,
        description="List of specific metrics cited in the response",
    )


class AgentResponse(BaseModel):
    """Structured response from the AI Operations Agent."""
    query: str = Field(description="Original user query")
    intent: str = Field(description="Classified intent of the query")
    response: str = Field(description="Natural language response with recommendations")
    response_ur: Optional[str] = Field(
        default=None,
        description="Urdu translation of the response (when requested)",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data backing the response",
    )
    grounding: AgentGroundingInfo = Field(
        description="Evidence grounding metadata",
    )
    language: str = Field(default="en", description="Response language")
    agent_mode: str = Field(
        default="rule_based",
        description="Agent processing mode (rule_based or llm_enhanced)",
    )
    llm_provider: str = Field(
        default="none",
        description="Configured LLM provider (none if rule-based only)",
    )


class AgentCapabilitiesResponse(BaseModel):
    """Describes the AI agent's available capabilities."""
    agent_name: str = Field(default="QueueWise AI Operations Agent")
    agent_mode: str = Field(description="Current agent mode")
    llm_provider: str = Field(description="Configured LLM provider")
    supported_intents: List[str] = Field(
        description="List of supported query intents",
    )
    example_queries: List[Dict[str, str]] = Field(
        description="Example queries for each intent",
    )
