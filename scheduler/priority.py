"""
Priority-based scheduler.

Jobs with the lowest priority NUMBER run first (1 = highest priority, 10 = lowest).
This is the same min-heap approach as SJF, but keyed on priority instead of duration.

Data structure: min-heap
- enqueue: heappush → O(log n)
- dequeue: heappop  → O(log n)

When to use: when some jobs are more important than others.
Example: payment processing (priority=1) should run before
report generation (priority=8).

Downside: same starvation problem as SJF — low-priority jobs
might wait forever if high-priority jobs keep arriving.
A fix would be "aging": gradually increase priority of waiting
jobs. We don't implement aging here, but it's a great interview
follow-up to mention.
"""

import heapq
from typing import Optional

from scheduler.base import AbstractScheduler, SchedulableJob


class PriorityScheduler(AbstractScheduler):

    def __init__(self):
        self._heap: list[tuple[int, int, SchedulableJob]] = []
        self._counter: int = 0

    def enqueue(self, job: SchedulableJob) -> None:
        heapq.heappush(self._heap, (job.priority, self._counter, job))
        self._counter += 1

    def dequeue(self) -> Optional[SchedulableJob]:
        if self._heap:
            _, _, job = heapq.heappop(self._heap)
            return job
        return None

    def peek(self) -> Optional[SchedulableJob]:
        return self._heap[0][2] if self._heap else None

    def size(self) -> int:
        return len(self._heap)

    @property
    def policy_name(self) -> str:
        return "priority"
