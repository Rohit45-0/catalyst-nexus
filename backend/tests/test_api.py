"""
Catalyst Nexus Core - Test Suite
================================

Automated tests using pytest.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for async tests."""
    return 'asyncio'


@pytest.fixture
async def client():
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestHealth:
    """Health check endpoint tests."""
    
    @pytest.mark.anyio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns status."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["service"] == "Catalyst Nexus Core"
    
    @pytest.mark.anyio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuth:
    """Authentication endpoint tests."""
    
    @pytest.mark.anyio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        # This would require a test database setup
        pass
    
    @pytest.mark.anyio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401


class TestProjects:
    """Project management endpoint tests."""
    
    @pytest.mark.anyio
    async def test_list_projects_unauthorized(self, client: AsyncClient):
        """Test listing projects without auth returns 401."""
        response = await client.get("/api/v1/projects")
        assert response.status_code == 401


class TestJobs:
    """Job management endpoint tests."""
    
    @pytest.mark.anyio
    async def test_list_jobs_unauthorized(self, client: AsyncClient):
        """Test listing jobs without auth returns 401."""
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 401


class TestMarketIntel:
    """Market intelligence endpoint tests."""

    @pytest.mark.anyio
    async def test_analyze_category_trends_unauthorized(self, client: AsyncClient):
        """Trend analysis endpoint should require authentication."""
        response = await client.post(
            "/api/v1/market-intel/analyze-category-trends",
            json={"category": "laptop"}
        )
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_generate_campaign_brief_unauthorized(self, client: AsyncClient):
        """Campaign brief endpoint should require authentication."""
        response = await client.post(
            "/api/v1/market-intel/generate-campaign-brief",
            json={
                "product_name": "Smart Laptop",
                "product_description": "High-performance laptop for creators with long battery life.",
                "category": "technology",
                "target_audience": "students and creators"
            }
        )
        assert response.status_code == 401


class TestVault:
    """Identity vault endpoint tests."""
    
    @pytest.mark.anyio
    async def test_list_identities_unauthorized(self, client: AsyncClient):
        """Test listing identities without auth returns 401."""
        response = await client.get("/api/v1/vault/identities")
        assert response.status_code == 401
