"""
QueueWise AI — API Router

Central router that aggregates all API sub-routers.
"""
from fastapi import APIRouter
from app.api.v1.tokens import router as tokens_router
from app.api.v1.services import router as services_router
from app.api.v1.counters import router as counters_router
from app.api.v1.queues import router as queues_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.websocket import router as websocket_router

from app.api.v1.simulation import router as simulation_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.agent import router as agent_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.voice import router as voice_router

api_router = APIRouter()


@api_router.get("/status", tags=["System"])
async def api_status():
    """API version status endpoint."""
    return {
        "api_version": "v1",
        "status": "operational",
    }


# Mounted routers
api_router.include_router(tokens_router, prefix="/tokens", tags=["Tokens"])
api_router.include_router(services_router, prefix="/services", tags=["Services"])
api_router.include_router(counters_router, prefix="/counters", tags=["Counters"])
api_router.include_router(queues_router, prefix="/queues", tags=["Queues"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(websocket_router, prefix="/ws", tags=["Real-Time"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
api_router.include_router(mcp_router, prefix="/mcp", tags=["Model Context Protocol (MCP)"])
api_router.include_router(voice_router, prefix="/voice", tags=["Voice & Speech"])

