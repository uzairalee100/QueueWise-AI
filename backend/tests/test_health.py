"""
QueueWise AI — Health and Foundation Tests

Verifies that the application starts, the health endpoint responds,
and the API router is mounted correctly.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    """Health check should return 200 with status healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "QueueWise AI"
    assert "version" in data
    assert "environment" in data


@pytest.mark.anyio
async def test_api_status_endpoint(client: AsyncClient):
    """API v1 status should return 200 with version info."""
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["status"] == "operational"


@pytest.mark.anyio
async def test_nonexistent_endpoint(client: AsyncClient):
    """Unknown endpoint should return 404."""
    response = await client.get("/api/v1/nonexistent")
    assert response.status_code == 404
