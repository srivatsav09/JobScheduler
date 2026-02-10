"""
Pydantic schemas for the /scheduler endpoints.

SchedulerConfig: request body for changing the active scheduling policy at runtime.
SchedulerStatus: response showing current scheduler state.
"""

from pydantic import BaseModel

from models.enums import SchedulingPolicy


class SchedulerConfig(BaseModel):
    """Request body for PUT /scheduler/policy."""

    policy: SchedulingPolicy  # must be one of: fcfs, sjf, priority, round_robin


class SchedulerStatus(BaseModel):
    """Response body for GET /scheduler/status."""

    current_policy: str
    queue_depth: int         # how many jobs are waiting in Redis ready queue
    dead_letter_count: int   # how many jobs permanently failed
