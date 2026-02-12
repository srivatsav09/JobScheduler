"""
Tests for Priority scheduler.

Priority dequeues jobs with the LOWEST priority number first (1 = highest).
Ties are broken by insertion order.
"""

from scheduler.priority import PriorityScheduler
from scheduler.base import SchedulableJob


def _make_job(job_id: str, priority: int) -> SchedulableJob:
    return SchedulableJob(
        job_id=job_id,
        job_type="sleep",
        priority=priority,
        estimated_duration=1.0,
        enqueued_at=0.0,
        payload={},
    )


def test_dequeues_highest_priority_first():
    """Core guarantee: lowest priority NUMBER = highest urgency = dequeued first."""
    scheduler = PriorityScheduler()
    scheduler.enqueue(_make_job("low", 10))
    scheduler.enqueue(_make_job("high", 1))
    scheduler.enqueue(_make_job("medium", 5))

    assert scheduler.dequeue().job_id == "high"
    assert scheduler.dequeue().job_id == "medium"
    assert scheduler.dequeue().job_id == "low"


def test_equal_priority_preserves_insertion_order():
    scheduler = PriorityScheduler()
    scheduler.enqueue(_make_job("first", 5))
    scheduler.enqueue(_make_job("second", 5))
    scheduler.enqueue(_make_job("third", 5))

    assert scheduler.dequeue().job_id == "first"
    assert scheduler.dequeue().job_id == "second"
    assert scheduler.dequeue().job_id == "third"


def test_dequeue_from_empty_returns_none():
    assert PriorityScheduler().dequeue() is None


def test_peek_returns_highest_priority():
    scheduler = PriorityScheduler()
    scheduler.enqueue(_make_job("low", 10))
    scheduler.enqueue(_make_job("high", 1))

    assert scheduler.peek().job_id == "high"
    assert scheduler.size() == 2


def test_mixed_priority_ordering():
    """Simulate a realistic mix of priorities."""
    scheduler = PriorityScheduler()
    scheduler.enqueue(_make_job("report", 8))     # low urgency
    scheduler.enqueue(_make_job("payment", 1))     # critical
    scheduler.enqueue(_make_job("email", 5))       # normal
    scheduler.enqueue(_make_job("alert", 2))       # high

    assert scheduler.dequeue().job_id == "payment"
    assert scheduler.dequeue().job_id == "alert"
    assert scheduler.dequeue().job_id == "email"
    assert scheduler.dequeue().job_id == "report"


def test_policy_name():
    assert PriorityScheduler().policy_name == "priority"
