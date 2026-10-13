"""
QueueWise AI — AI Agent REST API Endpoints

Exposes the AI Operations Agent via:
- POST /ask — Submit a natural language query
- GET  /capabilities — Discover agent capabilities and example queries
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.agents.ops_agent import OperationsAgent
from app.schemas.agent import (
    AgentQueryRequest,
    AgentResponse,
    AgentGroundingInfo,
    AgentCapabilitiesResponse,
)

router = APIRouter()


@router.post(
    "/ask",
    response_model=AgentResponse,
    summary="Ask the AI Operations Agent",
    description=(
        "Submit a natural language query about queue operations. "
        "The agent reads live queue data, applies rule-based reasoning, "
        "and returns evidence-grounded recommendations."
    ),
)
async def ask_agent(
    request: AgentQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Process a supervisor query through the AI Operations Agent."""
    result = await OperationsAgent.ask(
        session=session,
        query=request.query,
        session_id=request.session_id,
        language=request.language,
    )

    return AgentResponse(
        query=result["query"],
        intent=result["intent"],
        response=result["response"],
        response_ur=result.get("response_ur"),
        data=result.get("data", {}),
        grounding=AgentGroundingInfo(**result["grounding"]),
        language=result.get("language", "en"),
        agent_mode=result.get("agent_mode", "rule_based"),
        llm_provider=result.get("llm_provider", "none"),
    )


@router.get(
    "/capabilities",
    response_model=AgentCapabilitiesResponse,
    summary="AI Agent Capabilities",
    description="Discover what the AI Operations Agent can do and see example queries.",
)
async def agent_capabilities() -> AgentCapabilitiesResponse:
    """Return the agent's supported intents and example queries."""
    return AgentCapabilitiesResponse(
        agent_name="QueueWise AI Operations Agent",
        agent_mode="rule_based" if settings.llm_provider == "none" else "llm_enhanced",
        llm_provider=settings.llm_provider,
        supported_intents=[
            "status",
            "recommendation",
            "bottleneck",
            "counter",
            "service",
            "analytics",
            "greeting",
        ],
        example_queries=[
            {
                "intent": "status",
                "query_en": "What is the current queue status?",
                "query_ur": "قطار کی موجودہ صورتحال کیا ہے؟",
            },
            {
                "intent": "recommendation",
                "query_en": "How should we improve operations?",
                "query_ur": "آپریشنز کو بہتر کرنے کے لیے کیا کرنا چاہیے؟",
            },
            {
                "intent": "bottleneck",
                "query_en": "Are there any bottlenecks right now?",
                "query_ur": "کیا ابھی کوئی مسئلہ یا رکاوٹ ہے؟",
            },
            {
                "intent": "counter",
                "query_en": "How should we allocate counters?",
                "query_ur": "کاؤنٹرز کو کیسے تقسیم کریں؟",
            },
            {
                "intent": "service",
                "query_en": "How is the General Inquiries service performing?",
                "query_ur": "جنرل سروس کی کارکردگی کیسی ہے؟",
            },
            {
                "intent": "analytics",
                "query_en": "Show me the KPI metrics and performance report",
                "query_ur": "کارکردگی کے اعداد و شمار دکھائیں",
            },
        ],
    )
