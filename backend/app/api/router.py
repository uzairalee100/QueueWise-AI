"""
QueueWise AI — API Router

Central router that aggregates all API sub-routers.
New feature routers are added here as the project grows.
"""
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/status", tags=["System"])
async def api_status():
    """API version status endpoint."""
    return {
        "api_version": "v1",
        "status": "operational",
    }


# Future routers will be included here:
# api_router.include_router(tokens_router, prefix="/tokens", tags=["Tokens"])
# api_router.include_router(counters_router, prefix="/counters", tags=["Counters"])
# api_router.include_router(queues_router, prefix="/queues", tags=["Queues"])
# api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
# api_router.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
