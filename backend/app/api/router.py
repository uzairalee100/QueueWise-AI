"""
QueueWise AI — API Router

Central router that aggregates all API sub-routers.
"""
from fastapi import APIRouter
from app.api.v1.tokens import router as tokens_router
from app.api.v1.services import router as services_router
from app.api.v1.counters import router as counters_router

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

# Future routers will be added here in upcoming milestones:
# api_router.include_router(queues_router, prefix="/queues", tags=["Queues"])
# api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
# api_router.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
