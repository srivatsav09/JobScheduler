"""
First Come First Served (FCFS) scheduler.

The simplest scheduling policy: jobs run in the order they arrive.
Internally, this is just a FIFO queue (first in, first out).

Data structure: collections.deque
- enqueue: append to right  → O(1)
- dequeue: pop from left    → O(1)

When to use: when fairness matters more than efficiency.
Every job gets served in arrival order — no job gets starved.

Downside: a long-running job blocks everything behind it.
This is called the "convoy effect" — worth mentioning in interviews.
"""

from collections import deque
from typing import Optional

from scheduler.base import AbstractScheduler, SchedulableJob


class FCFSScheduler(AbstractScheduler):

    def __init__(self):
        self._queue: deque[SchedulableJob] = deque()

    def enqueue(self, job: SchedulableJob) -> None:
        self._queue.append(job)

    def dequeue(self) -> Optional[SchedulableJob]:
        return self._queue.popleft() if self._queue else None

    def peek(self) -> Optional[SchedulableJob]:
        return self._queue[0] if self._queue else None

    def size(self) -> int:
        return len(self._queue)

    @property
    def policy_name(self) -> str:
        return "fcfs"
