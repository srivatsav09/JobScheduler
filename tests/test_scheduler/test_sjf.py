"""
Tests for SJF (Shortest Job First) scheduler.

SJF dequeues jobs with the smallest estimated_duration first.
Ties are broken by insertion order (the counter tiebreaker).
"""

from scheduler.sjf import SJFScheduler
from scheduler.base import SchedulableJob


def _make_job(job_id: str, duration: float) -> SchedulableJob:
    return SchedulableJob(
        job_id=job_id,
        job_type="sleep",
        priority=5,
        estimated_duration=duration,
        enqueued_at=0.0,
        payload={},
    )


def test_dequeues_shortest_first():
    """Core SJF guarantee: shortest estimated_duration comes out first."""
    scheduler = SJFScheduler()
    scheduler.enqueue(_make_job("long", 10.0))
    scheduler.enqueue(_make_job("short", 1.0))
    scheduler.enqueue(_make_job("medium", 5.0))

    assert scheduler.dequeue().job_id == "short"
    assert scheduler.dequeue().job_id == "medium"
    assert scheduler.dequeue().job_id == "long"


def test_equal_duration_preserves_insertion_order():
    """When durations are equal, the tiebreaker counter gives FCFS behavior."""
    scheduler = SJFScheduler()
    scheduler.enqueue(_make_job("first", 3.0))
    scheduler.enqueue(_make_job("second", 3.0))
    scheduler.enqueue(_make_job("third", 3.0))

    assert scheduler.dequeue().job_id == "first"
    assert scheduler.dequeue().job_id == "second"
    assert scheduler.dequeue().job_id == "third"


def test_dequeue_from_empty_returns_none():
    assert SJFScheduler().dequeue() is None


def test_peek_returns_shortest():
    scheduler = SJFScheduler()
    scheduler.enqueue(_make_job("long", 10.0))
    scheduler.enqueue(_make_job("short", 1.0))

    assert scheduler.peek().job_id == "short"
    assert scheduler.size() == 2  # peek doesn't remove


def test_size():
    scheduler = SJFScheduler()
    scheduler.enqueue(_make_job("a", 1.0))
    scheduler.enqueue(_make_job("b", 2.0))
    assert scheduler.size() == 2

    scheduler.dequeue()
    assert scheduler.size() == 1


def test_policy_name():
    assert SJFScheduler().policy_name == "sjf"
