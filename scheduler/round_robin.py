"""
Round Robin scheduler.

Each job gets a fixed time quantum (e.g., 5 seconds). If the job
finishes within the quantum, great. If not, it gets moved to the
back of the queue and the next job runs.

Data structure: deque (same as FCFS)
- enqueue: append to right → O(1)
- dequeue: pop from left   → O(1)
- requeue: append to right → O(1)  ← this is the key difference from FCFS

The extra method `requeue()` is what makes Round Robin special.
When a worker finishes a time quantum and the job isn't done,
it calls requeue() to send the job to the back of the line.

When to use: when fairness is critical — no job should wait
too long because another job is hogging resources.

Tradeoff: more context switching overhead (starting/stopping jobs),
but better responsiveness. The quantum size controls this tradeoff:
- Small quantum (1s): very fair, lots of switching overhead
- Large quantum (60s): less fair, approaches FCFS behavior

For our job scheduler (as opposed to a CPU scheduler), Round Robin
means: short jobs finish quickly even when long jobs are in the queue.
"""

from collections import deque
from typing import Optional

from scheduler.base import AbstractScheduler, SchedulableJob


class RoundRobinScheduler(AbstractScheduler):

    def __init__(self, time_quantum: float = 5.0):
        self._queue: deque[SchedulableJob] = deque()
        self.time_quantum = time_quantum

    def enqueue(self, job: SchedulableJob) -> None:
        self._queue.append(job)

    def dequeue(self) -> Optional[SchedulableJob]:
        return self._queue.popleft() if self._queue else None

    def requeue(self, job: SchedulableJob) -> None:
        """
        Send a job to the back of the line after its quantum expires.

        This is the core of Round Robin — FCFS doesn't have this method.
        The worker calls this when a job's time quantum runs out but
        the job isn't finished yet.
        """
        self._queue.append(job)

    def peek(self) -> Optional[SchedulableJob]:
        return self._queue[0] if self._queue else None

    def size(self) -> int:
        return len(self._queue)

    @property
    def policy_name(self) -> str:
        return "round_robin"
