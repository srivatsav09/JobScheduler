"""
Worker pool — manages a thread pool that executes jobs from Redis.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    WorkerPool                            │
    │                                                         │
    │  Dispatcher Thread                                      │
    │  ┌───────────────────────┐                              │
    │  │ BLPOP from Redis      │  ← blocks until a job       │
    │  │ (ready queue)         │    arrives, zero polling     │
    │  └──────────┬────────────┘                              │
    │             │ submit()                                   │
    │             ▼                                            │
    │  ┌──────────────────────────────────────────┐           │
    │  │ ThreadPoolExecutor (4 threads)            │           │
    │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
    │  │  │Thread 1│ │Thread 2│ │Thread 3│ │Thread 4│       │
    │  │  │execute │ │execute │ │execute │ │(idle)  │       │
    │  │  └────────┘ └────────┘ └────────┘ └────────┘       │
    │  └──────────────────────────────────────────┘           │
    └─────────────────────────────────────────────────────────┘

The dispatcher thread uses Redis BLPOP (blocking list pop).
Unlike polling (check → sleep → check → sleep), BLPOP:
- Blocks until a job arrives (or timeout)
- Uses zero CPU while waiting
- Delivers the job instantly when one appears
- Is the standard Redis pattern for worker queues

When a job arrives, the dispatcher submits it to the ThreadPoolExecutor.
The executor has N threads (default 4), so up to N jobs run simultaneously.
If all threads are busy, submit() blocks until one becomes free.
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from redis import Redis

from config.settings import settings
from scheduler.engine import SchedulerEngine
from worker.executor import JobExecutor

logger = logging.getLogger(__name__)


class WorkerPool:

    def __init__(self, redis_client: Redis, db_session_factory):
        self._redis = redis_client
        self._executor = ThreadPoolExecutor(
            max_workers=settings.WORKER_POOL_SIZE,
            thread_name_prefix="job-worker",
        )
        self._job_executor = JobExecutor(db_session_factory, redis_client)
        self._running = False

    def start(self) -> None:
        """Start the dispatcher thread that feeds jobs to the thread pool."""
        self._running = True
        dispatcher = threading.Thread(target=self._dispatch_loop, daemon=True)
        dispatcher.start()
        logger.info(f"Worker pool started with {settings.WORKER_POOL_SIZE} threads")

    def stop(self) -> None:
        """Signal the dispatcher to stop, then shut down the thread pool."""
        self._running = False
        self._executor.shutdown(wait=True)
        logger.info("Worker pool stopped")

    def _dispatch_loop(self) -> None:
        """
        Continuously pop jobs from Redis and submit them to the thread pool.

        BLPOP returns (key, value) when a job is available, or None on timeout.
        The 1-second timeout ensures we check self._running periodically
        so the loop can exit cleanly on shutdown.
        """
        while self._running:
            try:
                # BLPOP blocks for up to 1 second
                # Returns (queue_name, raw_json) or None
                result = self._redis.blpop(
                    SchedulerEngine.REDIS_READY_QUEUE, timeout=1
                )
                if result is None:
                    continue  # timeout, loop again (check self._running)

                _, raw_data = result
                job_data = json.loads(raw_data)

                logger.debug(f"Dispatching job {job_data['job_id']} to thread pool")

                # Submit to a thread. If all threads are busy, this blocks
                # until one becomes available — natural backpressure.
                future: Future = self._executor.submit(
                    self._job_executor.execute, job_data
                )
                future.add_done_callback(self._on_job_done)

            except Exception as e:
                logger.error(f"Dispatch error: {e}", exc_info=True)

    def _on_job_done(self, future: Future) -> None:
        """
        Callback fired when a worker thread finishes executing a job.

        This runs in the thread that completed the job, not the dispatcher.
        We use it only for logging unhandled exceptions — all normal
        success/failure handling happens inside JobExecutor.execute().
        """
        try:
            exc = future.exception()
            if exc:
                logger.error(f"Unhandled worker exception: {exc}")
        except Exception as e:
            logger.error(f"Callback error: {e}")
