"""
Job executor — runs a single job inside a worker thread.

This is the code that actually DOES THE WORK. Each worker thread calls
executor.execute(job_data), and this method handles the full lifecycle:

    1. Look up the job in Postgres, mark it RUNNING
    2. Find the right handler (SleepJob, WordCountJob, ThumbnailJob)
    3. Call handler.run(payload)
    4. On success: mark COMPLETED, store the result
    5. On failure: delegate to RetryHandler (which decides retry vs dead-letter)

Every database operation uses a SYNC session because this runs in a thread,
not in the async event loop. This is why models/base.py has two engines.

Thread safety:
- Each execute() call gets its OWN database session (created and closed within)
- Job handlers are stateless (no shared mutable state)
- The only shared resource is Redis (which is thread-safe by design)
So multiple threads can call execute() simultaneously without locks.
"""

import logging
import time
import uuid as _uuid
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from models.job import Job
from models.enums import JobStatus
from jobs.registry import get_job_handler
from worker.retry import RetryHandler

logger = logging.getLogger(__name__)


class JobExecutor:

    def __init__(self, db_session_factory, redis_client: Redis):
        self._db_session_factory = db_session_factory
        self._retry_handler = RetryHandler(redis_client)

    def execute(self, job_data: dict) -> dict:
        """
        Execute a single job. Called by WorkerPool from a thread.

        Args:
            job_data: dict deserialized from the Redis ready queue, containing
                      job_id, job_type, payload, etc.

        Returns:
            dict with execution status (for logging/debugging, not stored)
        """
        job_id = job_data["job_id"]
        job_type = job_data["job_type"]
        payload = job_data["payload"]

        session: Session = self._db_session_factory()
        try:
            # ── Step 1: Mark RUNNING ────────────────────────────
            job = session.query(Job).filter(Job.id == _uuid.UUID(job_id)).first()
            if job is None:
                logger.warning(f"Job {job_id} not found in DB, skipping")
                return {"status": "skipped", "job_id": job_id}

            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.now(timezone.utc)
            session.commit()

            # ── Step 2: Find handler and execute ────────────────
            handler = get_job_handler(job_type)
            start_time = time.monotonic()
            result = handler.run(payload)
            elapsed = time.monotonic() - start_time

            # ── Step 3: Mark COMPLETED ──────────────────────────
            job.status = JobStatus.COMPLETED.value
            job.result = {**result, "execution_time_sec": round(elapsed, 3)}
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(f"Job {job_id} [{job_type}] completed in {elapsed:.3f}s")
            return {"status": "completed", "job_id": job_id}

        except Exception as e:
            # ── Step 4: Handle failure ──────────────────────────
            session.rollback()
            logger.error(f"Job {job_id} [{job_type}] failed: {e}")

            # RetryHandler decides: retry or dead-letter
            self._retry_handler.handle_failure(job_id, str(e), session)
            return {"status": "failed", "job_id": job_id, "error": str(e)}

        finally:
            # Always close the session — prevents connection leaks
            session.close()
