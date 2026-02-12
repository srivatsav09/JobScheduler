"""
Worker process entry point.

This is a SEPARATE process from the FastAPI API server.
It runs two components in the same process:

    1. SchedulerEngine — polls Postgres for PENDING jobs,
       applies the scheduling policy, pushes to Redis ready queue
    2. WorkerPool — pops jobs from Redis ready queue,
       executes them in a thread pool

Both run as daemon threads. The main thread just waits for
Ctrl+C (SIGINT) or a kill signal (SIGTERM) to shut down gracefully.

To run:
    python -m worker.main

In Docker:
    command: python -m worker.main

Why both in the same process?
    Simplicity. The scheduler and workers could be separate processes,
    but for this project, keeping them together avoids extra Docker
    services and inter-process communication complexity. In a larger
    system, you'd separate them so you could have 1 scheduler + N workers.
"""

import logging
import signal
import sys
import threading

from redis import Redis

from config.settings import settings
from models.base import Base, sync_engine, SyncSessionLocal
from scheduler.engine import SchedulerEngine
from worker.pool import WorkerPool

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    # Ensure tables exist before the scheduler tries to query them.
    # This is safe to call multiple times — if the API already created
    # the tables, this is a no-op. Solves the race condition where
    # the worker starts before the API has finished creating tables.
    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(sync_engine)

    redis_client = Redis.from_url(settings.redis_url)

    # Start the scheduler engine (polls DB → policy queue → Redis)
    engine = SchedulerEngine(redis_client, SyncSessionLocal)
    engine.start()

    # Start the worker pool (Redis → thread pool → execute jobs)
    pool = WorkerPool(redis_client, SyncSessionLocal)
    pool.start()

    # ── Graceful shutdown on Ctrl+C or SIGTERM ──────────────────
    shutdown_event = threading.Event()

    def shutdown(signum, frame):
        logger.info("Shutdown signal received, stopping...")
        engine.stop()
        pool.stop()
        shutdown_event.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Worker process running. Press Ctrl+C to stop.")

    # Block the main thread until shutdown signal
    # (using Event.wait() instead of signal.pause() for Windows compatibility)
    shutdown_event.wait()

    logger.info("Worker process exited")


if __name__ == "__main__":
    main()
