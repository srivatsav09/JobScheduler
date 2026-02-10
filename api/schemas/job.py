"""
Pydantic schemas for the /jobs endpoints.

These are NOT database models — they define the HTTP API contract:
- JobCreate: what the user sends when submitting a job (request body)
- JobResponse: what we send back for a single job (response body)
- JobListResponse: paginated list of jobs
- JobStats: aggregate statistics across all jobs

FastAPI validates incoming data against these automatically.
If someone sends priority=99, FastAPI returns a 422 error before our code even runs.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from models.enums import JobType, JobStatus


class JobCreate(BaseModel):
    """Request body for POST /jobs/ — what the user provides to submit a job."""

    name: str = Field(
        ...,  # ... means required, no default
        min_length=1,
        max_length=255,
        examples=["Count words in report.txt"],
    )
    job_type: JobType  # must be one of: word_count, thumbnail, sleep
    priority: int = Field(
        default=5,
        ge=1,   # greater than or equal to 1
        le=10,  # less than or equal to 10
        description="1 = highest priority, 10 = lowest",
    )
    estimated_duration: float = Field(
        default=1.0,
        gt=0,  # must be positive
        description="Estimated seconds to complete (used by SJF scheduler)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )
    payload: dict = Field(
        default_factory=dict,
        examples=[{"file_path": "/data/sample.txt"}],
    )


class JobResponse(BaseModel):
    """Response body for a single job — returned by GET /jobs/{id} and POST /jobs/."""

    id: UUID
    name: str
    job_type: str
    status: str
    priority: int
    estimated_duration: float
    payload: dict
    result: Optional[dict] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # from_attributes=True tells Pydantic to read from SQLAlchemy model attributes
    # (e.g., job.name) instead of requiring a dict (e.g., {"name": "..."})
    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Paginated list of jobs — returned by GET /jobs/."""

    jobs: list[JobResponse]
    total: int       # total matching jobs (ignoring pagination)
    page: int        # current page number
    page_size: int   # jobs per page


class JobStats(BaseModel):
    """Aggregate job statistics — returned by GET /jobs/stats."""

    total_jobs: int
    pending: int
    scheduled: int
    running: int
    completed: int
    failed: int
    avg_execution_time_ms: Optional[float] = None
