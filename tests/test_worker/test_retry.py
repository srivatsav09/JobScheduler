"""
Tests for the RetryHandler.

These test the decision logic:
- If retries remain → job goes back to PENDING
- If retries exhausted → job goes to FAILED + dead-letter queue
"""

import json
import uuid

import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.job import Job
from models.enums import JobStatus
from worker.retry import RetryHandler
from scheduler.engine import SchedulerEngine


def _setup():
    """Create an in-memory SQLite database and a fake Redis for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    session = Session()
    redis_client = fakeredis.FakeRedis()
    return session, redis_client


def _create_job(session, max_retries=3, retry_count=0):
    """Insert a test job into the database."""
    job = Job(
        id=uuid.uuid4(),
        name="test job",
        job_type="sleep",
        status=JobStatus.RUNNING.value,
        max_retries=max_retries,
        retry_count=retry_count,
        payload={"duration": 1.0},
    )
    session.add(job)
    session.commit()
    return job


def test_retry_sets_status_to_pending():
    """First failure with retries left → back to PENDING."""
    session, redis = _setup()
    job = _create_job(session, max_retries=3, retry_count=0)

    handler = RetryHandler(redis)
    handler.handle_failure(str(job.id), "something broke", session)

    session.refresh(job)
    assert job.status == JobStatus.PENDING.value
    assert job.retry_count == 1
    assert job.error_message == "something broke"


def test_retry_increments_count():
    """Each failure increments retry_count."""
    session, redis = _setup()
    job = _create_job(session, max_retries=3, retry_count=1)

    handler = RetryHandler(redis)
    handler.handle_failure(str(job.id), "failed again", session)

    session.refresh(job)
    assert job.retry_count == 2
    assert job.status == JobStatus.PENDING.value


def test_exhausted_retries_sets_failed():
    """When retry_count reaches max_retries → FAILED."""
    session, redis = _setup()
    job = _create_job(session, max_retries=2, retry_count=2)

    handler = RetryHandler(redis)
    handler.handle_failure(str(job.id), "final failure", session)

    session.refresh(job)
    assert job.status == JobStatus.FAILED.value
    assert job.retry_count == 3
    assert job.completed_at is not None


def test_exhausted_retries_pushes_to_dlq():
    """FAILED jobs should appear in the Redis dead-letter queue."""
    session, redis = _setup()
    job = _create_job(session, max_retries=1, retry_count=1)

    handler = RetryHandler(redis)
    handler.handle_failure(str(job.id), "permanent failure", session)

    # Check Redis DLQ
    dlq_entries = redis.lrange(SchedulerEngine.REDIS_DLQ_KEY, 0, -1)
    assert len(dlq_entries) == 1

    entry = json.loads(dlq_entries[0])
    assert entry["job_id"] == str(job.id)
    assert entry["error"] == "permanent failure"


def test_nonexistent_job_is_handled_gracefully():
    """If job_id doesn't exist in DB, handler should not crash."""
    session, redis = _setup()

    handler = RetryHandler(redis)
    # Should not raise
    handler.handle_failure(str(uuid.uuid4()), "error", session)
