"""
Job ORM model — maps to the "jobs" table in PostgreSQL.

Key design decisions:
- UUID primary key: prevents enumeration attacks, no sequential IDs to guess
- JSONB for payload/result: each job type can store different data without schema changes
- estimated_duration: used by SJF scheduler to decide ordering
- priority: used by Priority scheduler (1 = highest, 10 = lowest)
- Timestamps at every lifecycle stage: enables latency measurement for benchmarking
  (e.g., "how long did scheduling take?" = scheduled_at - created_at)
- retry_count + max_retries: drives the retry/dead-letter logic
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    # ── Identity ────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Scheduling fields ───────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.PENDING.value, nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False
    )
    estimated_duration: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    # ── Payload & Results ───────────────────────────────────────
    # JSONB lets each job type store different data:
    #   word_count job: {"file_path": "/data/sample.txt"}
    #   thumbnail job:  {"input_path": "/data/img.jpg", "width": 128}
    #   sleep job:      {"duration": 5.0, "fail_probability": 0.3}
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Retry tracking ──────────────────────────────────────────
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # ── Lifecycle timestamps ────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} [{self.job_type}] {self.status}>"
