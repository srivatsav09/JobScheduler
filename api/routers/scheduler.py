"""
Scheduler control endpoints.

PUT  /scheduler/policy      → Switch scheduling policy at runtime
GET  /scheduler/status      → View current policy, queue depth, DLQ count
GET  /scheduler/dead-letter → List all permanently failed jobs

The key feature here: you can switch between FCFS, SJF, Priority, and
Round Robin WITHOUT restarting the system. The active policy is stored
in a Redis key. The scheduler engine (in the worker process) reads this
key on every loop tick and rebuilds its internal queue if the policy changed.

This is a great interview talking point — runtime configuration.
"""

import json

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from api.dependencies import get_redis
from api.schemas.scheduler import SchedulerConfig, SchedulerStatus

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# These keys must match what the scheduler engine uses
REDIS_POLICY_KEY = "jobscheduler:policy"
REDIS_READY_QUEUE = "jobscheduler:ready"
REDIS_DLQ_KEY = "jobscheduler:dead_letter"


@router.put("/policy", response_model=SchedulerStatus)
async def set_scheduling_policy(
    config: SchedulerConfig,
    redis: Redis = Depends(get_redis),
) -> SchedulerStatus:
    """
    Switch the active scheduling policy.

    How it works:
    1. This endpoint writes the new policy name to Redis
    2. The scheduler engine (in worker process) reads this key every 0.5s
    3. If the policy changed, it rebuilds its internal queue
    4. All pending jobs are re-ordered according to the new policy

    No restart required. This is runtime reconfiguration.
    """
    await redis.set(REDIS_POLICY_KEY, config.policy.value)

    queue_depth = await redis.llen(REDIS_READY_QUEUE)
    dlq_count = await redis.llen(REDIS_DLQ_KEY)

    return SchedulerStatus(
        current_policy=config.policy.value,
        queue_depth=queue_depth,
        dead_letter_count=dlq_count,
    )


@router.get("/status", response_model=SchedulerStatus)
async def get_scheduler_status(
    redis: Redis = Depends(get_redis),
) -> SchedulerStatus:
    """Get current scheduler state."""
    policy = await redis.get(REDIS_POLICY_KEY)
    current_policy = policy.decode() if policy else "fcfs"
    queue_depth = await redis.llen(REDIS_READY_QUEUE)
    dlq_count = await redis.llen(REDIS_DLQ_KEY)

    return SchedulerStatus(
        current_policy=current_policy,
        queue_depth=queue_depth,
        dead_letter_count=dlq_count,
    )


@router.get("/dead-letter")
async def get_dead_letter_jobs(
    redis: Redis = Depends(get_redis),
) -> list[dict]:
    """
    List all jobs in the dead-letter queue.

    These are jobs that failed and exhausted all retries.
    In production, you'd have a process to review and either:
    - Fix the root cause and resubmit
    - Acknowledge and discard
    """
    raw_entries = await redis.lrange(REDIS_DLQ_KEY, 0, -1)
    return [json.loads(entry) for entry in raw_entries]
