"""
QueueWise AI — AI Operations Agent Test Suite

Verifies:
- Intent classification for all supported query types
- Agent tools return correct data from the database
- Agent produces grounded responses with cited metrics
- /api/v1/agent/ask endpoint processes queries end-to-end
- /api/v1/agent/capabilities returns supported intents
- Agent works fully in rule_based mode (LLM_PROVIDER=none)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ops_agent import OperationsAgent, classify_intent
from app.agents.tools import (
    tool_get_queue_snapshot,
    tool_get_analytics_summary,
    tool_get_optimization_recommendation,
    tool_get_bottleneck_analysis,
    tool_get_service_details,
)


# ──────────────── Intent Classification ────────────────

class TestIntentClassification:
    """Verify keyword-based intent classification."""

    def test_greeting_intent(self):
        assert classify_intent("Hello!") == "greeting"
        assert classify_intent("Salam") == "greeting"
        assert classify_intent("Hi there") == "greeting"

    def test_status_intent(self):
        assert classify_intent("What is the current queue status?") == "status"
        assert classify_intent("How many people are waiting?") == "status"
        assert classify_intent("Kitne log queue mein hain?") == "status"

    def test_recommendation_intent(self):
        assert classify_intent("What do you recommend?") == "recommendation"
        assert classify_intent("How can we improve wait times?") == "recommendation"
        assert classify_intent("Suggest better staffing") == "recommendation"

    def test_bottleneck_intent(self):
        assert classify_intent("Are there any bottlenecks?") == "bottleneck"
        assert classify_intent("Which service is slow?") == "bottleneck"
        assert classify_intent("Is anything stuck or stalled?") == "bottleneck"

    def test_counter_intent(self):
        assert classify_intent("How should we allocate counters?") == "counter"
        assert classify_intent("How many desks should be open?") == "counter"

    def test_service_intent(self):
        assert classify_intent("How is the registration service?") == "service"
        assert classify_intent("Blood test service performance") == "service"

    def test_analytics_intent(self):
        assert classify_intent("Show me the KPI metrics") == "analytics"
        assert classify_intent("What is the SLA compliance?") == "analytics"
        assert classify_intent("Average wait time report") == "analytics"

    def test_unknown_defaults_to_status(self):
        assert classify_intent("xyzabc") == "status"


# ──────────────── Agent Tools (Database Layer) ────────────────

@pytest.mark.anyio
class TestAgentTools:
    """Verify read-only tools return correct data structure from the database."""

    async def test_queue_snapshot_structure(self, db_session: AsyncSession):
        """Queue snapshot must include services, counters, and aggregate totals."""
        result = await tool_get_queue_snapshot(db_session, "default")
        assert "timestamp" in result
        assert "total_waiting" in result
        assert "total_serving" in result
        assert "active_counters" in result
        assert "total_counters" in result
        assert "services" in result
        assert isinstance(result["services"], list)
        assert "counters" in result
        assert isinstance(result["counters"], list)

    async def test_queue_snapshot_services_have_required_fields(self, db_session: AsyncSession):
        """Each service in snapshot has code, name, waiting, serving, etc."""
        result = await tool_get_queue_snapshot(db_session, "default")
        if result["services"]:
            svc = result["services"][0]
            assert "service_code" in svc
            assert "service_name" in svc
            assert "waiting" in svc
            assert "serving" in svc
            assert "avg_wait_seconds" in svc

    async def test_analytics_summary_structure(self, db_session: AsyncSession):
        """Analytics summary returns all expected KPI fields."""
        result = await tool_get_analytics_summary(db_session)
        assert "total_tokens_issued" in result
        assert "avg_wait_seconds" in result
        assert "sla_compliance_pct" in result

    async def test_optimization_recommendation_structure(self, db_session: AsyncSession):
        """Optimizer returns actionable recommendations with per-service detail."""
        result = await tool_get_optimization_recommendation(db_session)
        assert isinstance(result, dict)
        # Should have recommendations or an allocation
        assert "actionable_recommendations" in result or "error" in result

    async def test_bottleneck_analysis_structure(self, db_session: AsyncSession):
        """Bottleneck analysis returns bottlenecks, alerts, and summary."""
        result = await tool_get_bottleneck_analysis(db_session)
        assert "bottlenecks" in result
        assert "alerts" in result
        assert "snapshot_summary" in result
        assert isinstance(result["bottlenecks"], list)
        assert isinstance(result["alerts"], list)

    async def test_service_details_known_code(self, db_session: AsyncSession):
        """Service details returns data for a known service code."""
        result = await tool_get_service_details(db_session, "GEN")
        assert "error" not in result
        assert result["service_code"] == "GEN"
        assert "total_issued" in result
        assert "currently_waiting" in result

    async def test_service_details_unknown_code(self, db_session: AsyncSession):
        """Service details returns error for unknown code."""
        result = await tool_get_service_details(db_session, "NONEXISTENT")
        assert "error" in result


# ──────────────── Agent Grounded Responses ────────────────

@pytest.mark.anyio
class TestAgentGroundedResponses:
    """Verify the agent produces responses with proper grounding metadata."""

    async def test_status_response_grounding(self, db_session: AsyncSession):
        """Status response must cite data source and timestamp."""
        result = await OperationsAgent.ask(db_session, "What is the queue status?")
        assert result["intent"] == "status"
        assert "response" in result
        assert len(result["response"]) > 0
        assert "grounding" in result
        assert result["grounding"]["source"] == "live_queue_database"
        assert "timestamp" in result["grounding"]
        assert len(result["grounding"]["metrics_cited"]) > 0

    async def test_recommendation_response_grounding(self, db_session: AsyncSession):
        """Recommendation response includes optimizer source."""
        result = await OperationsAgent.ask(db_session, "What do you recommend?")
        assert result["intent"] == "recommendation"
        assert "grounding" in result
        assert "optimizer" in result["grounding"]["source"].lower() or "database" in result["grounding"]["source"].lower()

    async def test_greeting_response(self, db_session: AsyncSession):
        """Greeting includes quick status summary."""
        result = await OperationsAgent.ask(db_session, "Hello!")
        assert result["intent"] == "greeting"
        assert "QueueWise AI" in result["response"]

    async def test_analytics_response(self, db_session: AsyncSession):
        """Analytics response cites computed metrics."""
        result = await OperationsAgent.ask(db_session, "Show me the KPI metrics")
        assert result["intent"] == "analytics"
        assert "grounding" in result
        assert "analytics" in result["grounding"]["source"].lower()

    async def test_response_includes_agent_mode(self, db_session: AsyncSession):
        """Every response states the agent mode."""
        result = await OperationsAgent.ask(db_session, "Status")
        assert result["agent_mode"] == "rule_based"
        assert result["llm_provider"] == "none"

    async def test_urdu_language_preference(self, db_session: AsyncSession):
        """When language=ur, response includes Urdu marker."""
        result = await OperationsAgent.ask(db_session, "Status", language="ur")
        assert "response_ur" in result
        assert result["language"] == "ur"


# ──────────────── API Endpoint Integration Tests ────────────────

@pytest.mark.anyio
class TestAgentAPI:
    """End-to-end tests for the /api/v1/agent endpoints."""

    async def test_ask_endpoint_status_query(self, client: AsyncClient):
        """POST /agent/ask with a status query returns valid response."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "What is the current queue status?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "status"
        assert "response" in data
        assert len(data["response"]) > 0
        assert "grounding" in data
        assert data["grounding"]["source"] == "live_queue_database"
        assert data["agent_mode"] == "rule_based"

    async def test_ask_endpoint_recommendation_query(self, client: AsyncClient):
        """POST /agent/ask with recommendation query returns advice."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "What do you recommend to improve operations?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "recommendation"
        assert "response" in data
        assert "grounding" in data

    async def test_ask_endpoint_bottleneck_query(self, client: AsyncClient):
        """POST /agent/ask with bottleneck query identifies issues."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "Are there any bottleneck problems?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "bottleneck"

    async def test_ask_endpoint_counter_query(self, client: AsyncClient):
        """POST /agent/ask with counter query returns allocation analysis."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "How should we allocate counters?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "counter"

    async def test_ask_endpoint_service_query(self, client: AsyncClient):
        """POST /agent/ask asking about a specific service."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "How is the general service performing?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "service"

    async def test_ask_endpoint_analytics_query(self, client: AsyncClient):
        """POST /agent/ask for analytics/KPI data."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "Show me analytics and KPI report"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "analytics"

    async def test_ask_endpoint_greeting(self, client: AsyncClient):
        """POST /agent/ask with a greeting."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "Hello, good morning!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "greeting"

    async def test_ask_endpoint_urdu_language(self, client: AsyncClient):
        """POST /agent/ask with Urdu language preference."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": "Queue status?",
            "language": "ur",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "ur"
        assert data.get("response_ur") is not None

    async def test_ask_endpoint_empty_query_rejected(self, client: AsyncClient):
        """POST /agent/ask with empty query returns 422."""
        resp = await client.post("/api/v1/agent/ask", json={
            "query": ""
        })
        assert resp.status_code == 422

    async def test_capabilities_endpoint(self, client: AsyncClient):
        """GET /agent/capabilities returns agent metadata."""
        resp = await client.get("/api/v1/agent/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "QueueWise AI Operations Agent"
        assert "supported_intents" in data
        assert "status" in data["supported_intents"]
        assert "recommendation" in data["supported_intents"]
        assert "bottleneck" in data["supported_intents"]
        assert len(data["example_queries"]) > 0

    async def test_ask_endpoint_grounding_always_present(self, client: AsyncClient):
        """Every agent response must include grounding metadata — exit condition check."""
        queries = [
            "What is the status?",
            "Recommend something",
            "Any bottlenecks?",
            "Counter allocation?",
            "General service?",
            "KPI metrics?",
            "Hello",
        ]
        for query in queries:
            resp = await client.post("/api/v1/agent/ask", json={"query": query})
            assert resp.status_code == 200, f"Failed for query: {query}"
            data = resp.json()
            assert "grounding" in data, f"No grounding for query: {query}"
            assert "source" in data["grounding"], f"No source for query: {query}"
            assert "timestamp" in data["grounding"], f"No timestamp for query: {query}"
