"""
Scheduler Engine — the core orchestrator.

This runs in a daemon thread inside the worker process.
Every 0.5 seconds (configurable), it executes this loop:

    1. Check Redis: did someone change the scheduling policy?
       → If yes, rebuild the internal scheduler, re-enqueue all pending jobs
    2. Query Postgres: any new PENDING jobs?
       → If yes, mark them SCHEDULED, feed into the policy queue
    3. Dequeue from the policy queue → push to Redis ready queue
       → Workers (Phase 5) will BLPOP from this ready queue

This is the bridge between:
- The database (where jobs are stored)
- The scheduling policy (which decides ordering)
- The Redis ready queue (where workers consume from)

         Postgres                Policy Queue              Redis
    ┌──────────────┐       ┌──────────────────┐      ┌────────────┐
    │ PENDING jobs │──────>│ FCFS/SJF/Priority│─────>│ ready queue│
    │              │ ingest│ /RoundRobin      │ push │            │
    └──────────────┘       └──────────────────┘      └────────────┘
"""

import json
import time
import logging
import threading
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from config.settings import settings
from models.enums import JobStatus, SchedulingPolicy
from models.job import Job
from scheduler.base import SchedulableJob
from scheduler.registry import create_scheduler

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """
    Runs the scheduling loop in a background thread.

    The engine doesn't execute jobs — it only ORDERS them.
    Think of it as a traffic controller: it decides which car goes next,
    but doesn't drive the cars.
    """

    # Redis key names — shared with api/routers/scheduler.py
    REDIS_READY_QUEUE = "jobscheduler:ready"
    REDIS_POLICY_KEY = "jobscheduler:policy"
    REDIS_DLQ_KEY = "jobscheduler:dead_letter"

    def __init__(self, redis_client: Redis, db_session_factory):
        self._redis = redis_client
        self._db_session_factory = db_session_factory
        self._current_policy: str = settings.DEFAULT_SCHEDULING_POLICY
        self._scheduler = create_scheduler(SchedulingPolicy(self._current_policy))
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the scheduling loop in a daemon thread."""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info(f"Scheduler engine started with policy: {self._current_policy}")

    def stop(self) -> None:
        """Signal the loop to stop. It will finish its current tick and exit."""
        self._running = False

    def _run_loop(self) -> None:
        """
        The main loop. Runs until stop() is called.

        Each tick:
        1. Check if policy changed → rebuild scheduler if needed
        2. Ingest PENDING jobs from Postgres → feed into policy queue
        3. Dispatch from policy queue → push to Redis ready queue
        """
        while self._running:
            try:
                self._check_policy_change()
                self._ingest_pending_jobs()
                self._dispatch_to_ready_queue()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
            time.sleep(settings.WORKER_POLL_INTERVAL)

    def _check_policy_change(self) -> None:
        """
        Read the desired policy from Redis. If it changed, rebuild the scheduler.

        When the API writes a new policy via PUT /scheduler/policy,
        it sets the Redis key. We pick it up here.

        Critical detail: when switching policies, we DRAIN all jobs from the
        old scheduler and re-enqueue them into the new one. Otherwise jobs
        would be lost during the switch.
        """
        stored = self._redis.get(self.REDIS_POLICY_KEY)
        if not stored:
            return

        desired = stored.decode() if isinstance(stored, bytes) else stored
        if desired == self._current_policy:
            return

        logger.info(f"Policy change detected: {self._current_policy} → {desired}")
        old_scheduler = self._scheduler
        self._scheduler = create_scheduler(SchedulingPolicy(desired))

        # Drain old → new (re-enqueue preserves jobs, new policy re-orders them)
        drained = 0
        while (job := old_scheduler.dequeue()) is not None:
            self._scheduler.enqueue(job)
            drained += 1

        self._current_policy = desired
        if drained:
            logger.info(f"Re-enqueued {drained} jobs under new policy: {desired}")

    def _ingest_pending_jobs(self) -> None:
        """
        Pull PENDING jobs from Postgres, mark them SCHEDULED, add to policy queue.

        Why mark SCHEDULED in the database?
        - Prevents double-scheduling: next loop tick won't pick them up again
        - Creates an audit trail: you can see when a job was scheduled
        - Enables the state machine: PENDING → SCHEDULED → RUNNING → ...

        We limit to 50 jobs per tick to avoid holding a DB transaction too long.
        """
        session: Session = self._db_session_factory()
        try:
            pending_jobs = (
                session.query(Job)
                .filter(Job.status == JobStatus.PENDING.value)
                .order_by(Job.created_at)
                .limit(50)
                .all()
            )

            for job in pending_jobs:
                job.status = JobStatus.SCHEDULED.value
                job.scheduled_at = datetime.now(timezone.utc)

                # Convert ORM model → lightweight DTO for the scheduler
                schedulable = SchedulableJob(
                    job_id=str(job.id),
                    job_type=job.job_type,
                    priority=job.priority,
                    estimated_duration=job.estimated_duration,
                    enqueued_at=time.time(),
                    payload=job.payload,
                )
                self._scheduler.enqueue(schedulable)

            if pending_jobs:
                session.commit()
                logger.info(f"Ingested {len(pending_jobs)} pending jobs")

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _dispatch_to_ready_queue(self) -> None:
        """
        Move jobs from the policy queue to the Redis ready queue.

        After this, workers can pick them up via BLPOP.
        We serialize the job as JSON since Redis stores bytes/strings.
        """
        dispatched = 0
        while (job := self._scheduler.dequeue()) is not None:
            job_data = json.dumps({
                "job_id": job.job_id,
                "job_type": job.job_type,
                "priority": job.priority,
                "estimated_duration": job.estimated_duration,
                "payload": job.payload,
            })
            self._redis.rpush(self.REDIS_READY_QUEUE, job_data)
            dispatched += 1

        if dispatched:
            logger.info(f"Dispatched {dispatched} jobs to ready queue")
