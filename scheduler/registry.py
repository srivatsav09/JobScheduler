"""
Scheduler factory — maps policy names to scheduler classes.

This is the Factory pattern: instead of writing if/elif chains everywhere,
you have ONE place that knows how to create schedulers.

When someone asks in an interview: "How would you add a new scheduling policy?"
Answer: "Create the class, add one line to this registry."
"""

from models.enums import SchedulingPolicy
from scheduler.base import AbstractScheduler
from scheduler.fcfs import FCFSScheduler
from scheduler.sjf import SJFScheduler
from scheduler.priority import PriorityScheduler
from scheduler.round_robin import RoundRobinScheduler


_REGISTRY: dict[SchedulingPolicy, type[AbstractScheduler]] = {
    SchedulingPolicy.FCFS: FCFSScheduler,
    SchedulingPolicy.SJF: SJFScheduler,
    SchedulingPolicy.PRIORITY: PriorityScheduler,
    SchedulingPolicy.ROUND_ROBIN: RoundRobinScheduler,
}


def create_scheduler(policy: SchedulingPolicy, **kwargs) -> AbstractScheduler:
    """
    Create a scheduler instance for the given policy.

    For Round Robin, you can pass time_quantum as a kwarg:
        create_scheduler(SchedulingPolicy.ROUND_ROBIN, time_quantum=10.0)

    For all others, no kwargs needed.
    """
    cls = _REGISTRY.get(policy)
    if cls is None:
        raise ValueError(f"Unknown scheduling policy: {policy}")

    if policy == SchedulingPolicy.ROUND_ROBIN:
        return cls(**kwargs)
    return cls()
