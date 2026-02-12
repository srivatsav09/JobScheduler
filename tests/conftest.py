"""
Shared test fixtures.

These replace real infrastructure with lightweight in-memory alternatives:
- PostgreSQL → SQLite in memory (via aiosqlite)
- Redis → fakeredis (pure Python Redis mock)
- HTTP server → httpx.AsyncClient with ASGI transport (no network)

This means tests:
- Run without Docker
- Run in milliseconds (no network, no disk)
- Are fully isolated (each test gets a fresh database)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fakeredis.aioredis import FakeRedis

from models.base import Base
from api.main import create_app
from api.dependencies import get_db, get_redis

# SQLite in-memory database — created fresh for each test
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create a fresh in-memory database for each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create a database session bound to the test engine."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def fake_redis():
    """Create a fake Redis instance (in-memory, no real Redis needed)."""
    r = FakeRedis()
    yield r
    await r.flushall()


@pytest_asyncio.fixture
async def client(async_session, fake_redis):
    """
    Create a test HTTP client that talks directly to the FastAPI app.

    dependency_overrides tells FastAPI: "instead of using the real get_db
    and get_redis, use these test versions." This is how you test endpoints
    without a real database or Redis.

    ASGITransport means requests go directly to the app in-process,
    no HTTP server or network involved.
    """
    app = create_app()

    async def override_get_db():
        yield async_session

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
