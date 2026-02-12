"""Tests for the /health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health should return healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
