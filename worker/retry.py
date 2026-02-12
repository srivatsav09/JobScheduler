"""
Retry handler — decides what happens when a job fails.

Two outcomes:
1. retry_count < max_retries → set status back to PENDING, scheduler picks it up again
2. retry_count >= max_retries → set status to FAILED, push to dead-letter queue

The dead-letter queue (DLQ) is a Redis list that holds permanently failed jobs.
In production, someone would review the DLQ and either:
- Fix the root cause and resubmit the job
- Acknowledge the failure and clear it

Lifecycle on failure:
    RUNNING → (exception) → retry_count++ → PENDING  (if retries left)
    RUNNING → (exception) → retry_count++ → FAILED   (if retries exhausted → DLQ)

Why reset to PENDING instead of directly re-enqueuing?
Because the scheduler engine already polls for PENDING jobs every 0.5s.
By setting the status back to PENDING, we reuse the existing scheduling pipeline.
The job goes through the same path as a new job: PENDING → SCHEDULED → RUNNING.
No special retry queue needed — the scheduler handles it.
"""

import json
import logging
import uuid as _uuid
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from config.settings import settings
from models.job import Job
from models.enums import JobStatus
from scheduler.engine import SchedulerEngine

logger = logging.getLogger(__name__)


class RetryHandler:

    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def handle_failure(self, job_id: str, error_msg: str, session: Session) -> None:
        """
        Called by JobExecutor when a job raises an exception.

        Args:
            job_id: the UUID of the failed job
            error_msg: the exception message
            session: an open DB session (caller manages the transaction)
        """
        try:
            uid = _uuid.UUID(job_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid job_id format: {job_id}")
            return

        job = session.query(Job).filter(Job.id == uid).first()
        if job is None:
            logger.warning(f"Job {job_id} not found in DB during retry handling")
            return

        job.error_message = error_msg
        job.retry_count += 1

        if job.retry_count <= job.max_retries:
            # ── Retry: send back to PENDING ─────────────────────
            job.status = JobStatus.PENDING.value
            session.commit()
            logger.info(
                f"Job {job_id} will be retried "
                f"({job.retry_count}/{job.max_retries})"
            )
        else:
            # ── Exhausted: dead-letter queue ────────────────────
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

            self._push_to_dead_letter(job)
            logger.warning(
                f"Job {job_id} exhausted retries ({job.max_retries}), "
                f"moved to dead-letter queue"
            )

    def _push_to_dead_letter(self, job: Job) -> None:
        """Push a failed job's info to the Redis dead-letter list."""
        dlq_entry = json.dumps({
            "job_id": str(job.id),
            "job_type": job.job_type,
            "name": job.name,
            "error": job.error_message,
            "retry_count": job.retry_count,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })
        self._redis.rpush(SchedulerEngine.REDIS_DLQ_KEY, dlq_entry)
