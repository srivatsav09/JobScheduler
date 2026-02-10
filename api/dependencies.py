"""
FastAPI dependency injection.

How this works:
- An endpoint declares `db: AsyncSession = Depends(get_db)`
- FastAPI calls get_db() before your endpoint runs, creating a DB session
- Your endpoint receives the session and uses it
- After the endpoint returns (or raises), the session is automatically closed

This avoids:
- Opening/closing connections manually in every endpoint
- Forgetting to close connections (resource leak)
- Duplicating setup code
"""

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from models.base import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an async database session, auto-closes when the request ends."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    """Returns the Redis client stored on the app during startup."""
    return request.app.state.redis
