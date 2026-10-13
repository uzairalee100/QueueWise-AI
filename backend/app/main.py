"""
QueueWise AI — FastAPI Application Entry Point

Configures the FastAPI app with CORS, routers, lifespan events,
and the health endpoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, get_logger
from app.api.router import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging()
    logger.info(
        "starting_application",
        app_name=settings.app_name,
        environment=settings.app_env,
        database=settings.database_url.split("@")[-1] if "@" in settings.database_url else "sqlite",
    )

    # Initialize database tables (dev/demo only — production uses Alembic)
    if settings.app_env == "development":
        await init_db()
        logger.info("database_initialized", mode="auto-create")

    yield

    logger.info("shutting_down_application")


app = FastAPI(
    title=settings.app_name,
    description="Smarter Queues. Less Waiting. Better Public Services.",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring and deployment verification."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
    }
