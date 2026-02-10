"""
Health check endpoint.

This is the first thing you hit to verify the system is running.
It checks both Postgres and Redis connectivity.

In production, load balancers and container orchestrators (k8s) use
health endpoints to decide if a service is ready to receive traffic.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from api.dependencies import get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """Check that Postgres and Redis are reachable."""
    # Test Postgres: run a trivial query
    await db.execute(text("SELECT 1"))

    # Test Redis: ping-pong
    await redis.ping()

    return {"status": "healthy", "postgres": "ok", "redis": "ok"}
