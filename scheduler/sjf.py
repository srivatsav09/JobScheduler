"""
Shortest Job First (SJF) scheduler.

Jobs with the smallest estimated_duration get executed first.
This minimizes average waiting time across all jobs — it's provably optimal
for that metric (you'd learn this in an OS course).

Data structure: min-heap (via Python's heapq module)
- enqueue: heappush → O(log n)
- dequeue: heappop  → O(log n)

The heap stores tuples: (estimated_duration, counter, job)
- estimated_duration: the sorting key (shortest first)
- counter: tiebreaker — if two jobs have the same duration,
  the one enqueued first wins. Without this, Python would try to
  compare SchedulableJob objects, which would crash.

When to use: when you want to maximize throughput (finish the most
jobs in the least time).

Downside: starvation — a job with estimated_duration=1000 might never
run if short jobs keep arriving. Worth mentioning in interviews.
"""

import heapq
from typing import Optional

from scheduler.base import AbstractScheduler, SchedulableJob


class SJFScheduler(AbstractScheduler):

    def __init__(self):
        self._heap: list[tuple[float, int, SchedulableJob]] = []
        self._counter: int = 0  # monotonic tiebreaker for heap stability

    def enqueue(self, job: SchedulableJob) -> None:
        heapq.heappush(self._heap, (job.estimated_duration, self._counter, job))
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
        return "sjf"
