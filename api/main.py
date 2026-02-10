"""
FastAPI application factory.

This file:
1. Creates the FastAPI app
2. Runs startup logic (create DB tables, connect to Redis)
3. Registers all routers (jobs, scheduler, health)
4. Runs shutdown logic (close connections)

The `lifespan` context manager is FastAPI's way of handling startup/shutdown.
It replaces the older @app.on_event("startup") pattern.

To run:  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis as AsyncRedis

from config.settings import settings
from models.base import async_engine, Base
from api.routers import jobs, scheduler, health

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup (before yield) and shutdown (after yield).

    Startup:
    - Creates all DB tables if they don't exist (safe to run multiple times)
    - Connects to Redis
    - Sets the default scheduling policy

    Shutdown:
    - Closes Redis connection
    - Disposes the DB engine (closes connection pool)
    """
    # ── Startup ─────────────────────────────────────────────────
    logger.info("Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.redis = AsyncRedis.from_url(settings.redis_url)

    # Set default policy so the scheduler engine knows what to use
    await app.state.redis.set("jobscheduler:policy", settings.DEFAULT_SCHEDULING_POLICY)
    logger.info(f"API ready — default policy: {settings.DEFAULT_SCHEDULING_POLICY}")

    yield  # app is running and serving requests between startup and shutdown

    # ── Shutdown ────────────────────────────────────────────────
    await app.state.redis.close()
    await async_engine.dispose()
    logger.info("API shut down")


def create_app() -> FastAPI:
    """Factory function that builds and configures the FastAPI application."""
    app = FastAPI(
        title="Job Scheduler",
        description="A multithreaded job scheduler with pluggable scheduling policies (FCFS, SJF, Priority, Round Robin)",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register routers — each one adds its endpoints to the app
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(scheduler.router)

    return app


# This is what uvicorn imports: `uvicorn api.main:app`
app = create_app()
