"""
Abstract base class for all scheduling policies (Strategy pattern).

The Strategy pattern lets you swap algorithms at runtime without changing
the code that uses them. The SchedulerEngine only knows about AbstractScheduler —
it calls enqueue() and dequeue() without caring whether it's FCFS, SJF, etc.

To add a new scheduling policy:
1. Create a new class that inherits AbstractScheduler
2. Implement all 4 abstract methods
3. Register it in scheduler/registry.py

That's it. No other code needs to change.

SchedulableJob is a lightweight data transfer object (DTO) — just the fields
the scheduler needs to make decisions. It does NOT hold the full DB model,
keeping the scheduler layer independent of SQLAlchemy.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SchedulableJob:
    """
    Lightweight representation of a job for scheduling decisions.

    Why a separate class instead of using the Job ORM model?
    - Decoupling: schedulers don't need SQLAlchemy as a dependency
    - Testability: you can create SchedulableJob in tests without a database
    - Minimal data: only the fields needed for scheduling decisions
    """
    job_id: str
    job_type: str
    priority: int              # 1 = highest, 10 = lowest (used by PriorityScheduler)
    estimated_duration: float  # seconds (used by SJFScheduler)
    enqueued_at: float         # timestamp when added to scheduler (used by FCFS tiebreaking)
    payload: dict = field(default_factory=dict)


class AbstractScheduler(ABC):
    """
    Interface that all scheduling policies implement.

    4 methods — that's the entire contract:
    - enqueue: add a job
    - dequeue: remove and return the next job (according to this policy's rules)
    - peek: look at the next job without removing it
    - size: how many jobs are queued
    """

    @abstractmethod
    def enqueue(self, job: SchedulableJob) -> None:
        """Add a job to this scheduler's internal queue."""
        ...

    @abstractmethod
    def dequeue(self) -> Optional[SchedulableJob]:
        """Remove and return the next job to execute, or None if empty."""
        ...

    @abstractmethod
    def peek(self) -> Optional[SchedulableJob]:
        """View the next job without removing it. Returns None if empty."""
        ...

    @abstractmethod
    def size(self) -> int:
        """Return the number of jobs currently in the queue."""
        ...

    @property
    @abstractmethod
    def policy_name(self) -> str:
        """Unique name for this policy (e.g., 'fcfs', 'sjf')."""
        ...
