"""
SQLAlchemy engine and session factories.

Two separate engines exist because:
- FastAPI is async → needs asyncpg driver + async sessions
- Worker threads are sync → need psycopg2 driver + sync sessions

You CANNOT use an async session inside a thread (it would block the event loop),
and you CANNOT use a sync session inside an async handler (it would block the server).
This separation is the correct pattern for mixed async/sync Python apps.
"""

from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine

from config.settings import settings


class Base(DeclarativeBase):
    """Base class for all ORM models. SQLAlchemy uses this to track table metadata."""
    pass


# ── Async engine (for FastAPI) ──────────────────────────────────
async_engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

# ── Sync engine (for worker threads) ────────────────────────────
sync_engine = create_engine(settings.sync_database_url, echo=False)
SyncSessionLocal = sessionmaker(sync_engine)
