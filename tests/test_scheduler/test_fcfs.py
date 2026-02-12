"""
Tests for FCFS (First Come First Served) scheduler.

FCFS is a FIFO queue — jobs come out in the same order they went in.
These tests verify that guarantee and edge cases.
"""

from scheduler.fcfs import FCFSScheduler
from scheduler.base import SchedulableJob


def _make_job(job_id: str, **kwargs) -> SchedulableJob:
    """Helper to create a SchedulableJob with sensible defaults."""
    return SchedulableJob(
        job_id=job_id,
        job_type="sleep",
        priority=kwargs.get("priority", 5),
        estimated_duration=kwargs.get("estimated_duration", 1.0),
        enqueued_at=kwargs.get("enqueued_at", 0.0),
        payload={},
    )


def test_dequeue_order_matches_enqueue_order():
    """Core FCFS guarantee: first in, first out."""
    scheduler = FCFSScheduler()
    scheduler.enqueue(_make_job("first"))
    scheduler.enqueue(_make_job("second"))
    scheduler.enqueue(_make_job("third"))

    assert scheduler.dequeue().job_id == "first"
    assert scheduler.dequeue().job_id == "second"
    assert scheduler.dequeue().job_id == "third"


def test_dequeue_from_empty_returns_none():
    scheduler = FCFSScheduler()
    assert scheduler.dequeue() is None


def test_peek_returns_next_without_removing():
    scheduler = FCFSScheduler()
    scheduler.enqueue(_make_job("a"))
    scheduler.enqueue(_make_job("b"))

    assert scheduler.peek().job_id == "a"
    assert scheduler.peek().job_id == "a"  # still "a", not consumed
    assert scheduler.size() == 2


def test_size_tracks_enqueue_and_dequeue():
    scheduler = FCFSScheduler()
    assert scheduler.size() == 0

    scheduler.enqueue(_make_job("a"))
    assert scheduler.size() == 1

    scheduler.enqueue(_make_job("b"))
    assert scheduler.size() == 2

    scheduler.dequeue()
    assert scheduler.size() == 1


def test_policy_name():
    assert FCFSScheduler().policy_name == "fcfs"


def test_ignores_priority_and_duration():
    """FCFS doesn't care about priority or duration — only arrival order."""
    scheduler = FCFSScheduler()
    scheduler.enqueue(_make_job("low_priority", priority=10))
    scheduler.enqueue(_make_job("high_priority", priority=1))
    scheduler.enqueue(_make_job("short", estimated_duration=0.1))

    assert scheduler.dequeue().job_id == "low_priority"
    assert scheduler.dequeue().job_id == "high_priority"
    assert scheduler.dequeue().job_id == "short"
