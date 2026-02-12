"""
Tests for Round Robin scheduler.

Round Robin is FCFS with an extra feature: requeue().
When a job's time quantum expires, the worker calls requeue()
to send it to the back of the line.
"""

from scheduler.round_robin import RoundRobinScheduler
from scheduler.base import SchedulableJob


def _make_job(job_id: str) -> SchedulableJob:
    return SchedulableJob(
        job_id=job_id,
        job_type="sleep",
        priority=5,
        estimated_duration=1.0,
        enqueued_at=0.0,
        payload={},
    )


def test_dequeue_order_matches_enqueue_order():
    """Without requeue, Round Robin behaves like FCFS."""
    scheduler = RoundRobinScheduler(time_quantum=5.0)
    scheduler.enqueue(_make_job("a"))
    scheduler.enqueue(_make_job("b"))
    scheduler.enqueue(_make_job("c"))

    assert scheduler.dequeue().job_id == "a"
    assert scheduler.dequeue().job_id == "b"
    assert scheduler.dequeue().job_id == "c"


def test_requeue_sends_to_back():
    """The core Round Robin behavior: requeue moves job to the end."""
    scheduler = RoundRobinScheduler(time_quantum=5.0)
    scheduler.enqueue(_make_job("a"))
    scheduler.enqueue(_make_job("b"))
    scheduler.enqueue(_make_job("c"))

    # Dequeue "a", simulate it not finishing, requeue it
    job_a = scheduler.dequeue()
    assert job_a.job_id == "a"
    scheduler.requeue(job_a)

    # Now order should be: b, c, a
    assert scheduler.dequeue().job_id == "b"
    assert scheduler.dequeue().job_id == "c"
    assert scheduler.dequeue().job_id == "a"


def test_repeated_requeue_cycles():
    """Simulate multiple rounds of Round Robin execution."""
    scheduler = RoundRobinScheduler(time_quantum=2.0)
    scheduler.enqueue(_make_job("x"))
    scheduler.enqueue(_make_job("y"))

    # Round 1: x runs, gets requeued. y runs, gets requeued.
    job = scheduler.dequeue()
    assert job.job_id == "x"
    scheduler.requeue(job)

    job = scheduler.dequeue()
    assert job.job_id == "y"
    scheduler.requeue(job)

    # Round 2: x again, then y again
    assert scheduler.dequeue().job_id == "x"
    assert scheduler.dequeue().job_id == "y"


def test_time_quantum_is_configurable():
    scheduler = RoundRobinScheduler(time_quantum=10.0)
    assert scheduler.time_quantum == 10.0


def test_dequeue_from_empty_returns_none():
    assert RoundRobinScheduler().dequeue() is None


def test_policy_name():
    assert RoundRobinScheduler().policy_name == "round_robin"
