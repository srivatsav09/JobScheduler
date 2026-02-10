"""
Job CRUD endpoints.

POST /jobs/          → Submit a new job (persists to Postgres)
GET  /jobs/          → List jobs with filtering + pagination
GET  /jobs/stats     → Aggregate statistics (how many pending, completed, etc.)
GET  /jobs/{job_id}  → Get a single job by ID
DELETE /jobs/{job_id} → Cancel a pending/scheduled job

The API layer is intentionally thin:
- Validate input (Pydantic does this automatically)
- Talk to the database
- Return the response

It does NOT schedule or execute jobs — that's the scheduler's and worker's job.
Separation of concerns.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.dependencies import get_db
from api.schemas.job import JobCreate, JobResponse, JobListResponse, JobStats
from models.job import Job
from models.enums import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(
    job_in: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Submit a new job.

    The job is saved to Postgres with status=PENDING.
    The scheduler engine (running in the worker process) polls for PENDING jobs
    and moves them through the scheduling pipeline.

    We do NOT push to Redis here — that's the scheduler's responsibility.
    This keeps the API simple: just write to the database.
    """
    job = Job(
        name=job_in.name,
        job_type=job_in.job_type.value,
        priority=job_in.priority,
        estimated_duration=job_in.estimated_duration,
        max_retries=job_in.max_retries,
        payload=job_in.payload,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)  # reload to get server-generated fields (id, created_at)
    return JobResponse.model_validate(job)


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Jobs per page"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    List jobs with optional filtering and pagination.

    Pagination works with OFFSET/LIMIT:
    - page=1, page_size=20 → rows 0-19
    - page=2, page_size=20 → rows 20-39

    We run TWO queries:
    1. Count total matching rows (for the 'total' field)
    2. Fetch the actual page of rows

    This lets the frontend know "there are 150 jobs total, showing 20"
    even though we only return 20 rows.
    """
    # Build base filter conditions
    conditions = []
    if status:
        conditions.append(Job.status == status.value)
    if job_type:
        conditions.append(Job.job_type == job_type)

    # Query 1: total count
    count_query = select(func.count(Job.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total = (await db.execute(count_query)).scalar() or 0

    # Query 2: fetch page
    offset = (page - 1) * page_size
    query = (
        select(Job)
        .where(*conditions) if conditions else select(Job)
    )
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=JobStats)
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
) -> JobStats:
    """
    Aggregate job statistics.

    Returns counts per status + average execution time.
    This is a single query using conditional aggregation (COUNT + FILTER),
    which is much faster than running 6 separate COUNT queries.
    """
    query = select(
        func.count(Job.id).label("total"),
        func.count(Job.id).filter(Job.status == JobStatus.PENDING.value).label("pending"),
        func.count(Job.id).filter(Job.status == JobStatus.SCHEDULED.value).label("scheduled"),
        func.count(Job.id).filter(Job.status == JobStatus.RUNNING.value).label("running"),
        func.count(Job.id).filter(Job.status == JobStatus.COMPLETED.value).label("completed"),
        func.count(Job.id).filter(Job.status == JobStatus.FAILED.value).label("failed"),
    )
    row = (await db.execute(query)).one()

    # Average execution time for completed jobs (completed_at - started_at)
    avg_query = select(
        func.avg(
            func.extract("epoch", Job.completed_at) - func.extract("epoch", Job.started_at)
        )
    ).where(
        Job.status == JobStatus.COMPLETED.value,
        Job.started_at.is_not(None),
        Job.completed_at.is_not(None),
    )
    avg_seconds = (await db.execute(avg_query)).scalar()
    avg_ms = round(avg_seconds * 1000, 2) if avg_seconds else None

    return JobStats(
        total_jobs=row.total,
        pending=row.pending,
        scheduled=row.scheduled,
        running=row.running,
        completed=row.completed,
        failed=row.failed,
        avg_execution_time_ms=avg_ms,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get a single job by its UUID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=204)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Cancel a job.

    Only PENDING and SCHEDULED jobs can be cancelled — once a job is RUNNING,
    it's too late (the worker is already executing it).

    We don't delete the row — we set status to FAILED so it shows up
    in stats and history. Deleting data is almost never the right call.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in (JobStatus.PENDING.value, JobStatus.SCHEDULED.value):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel job in {job.status} state. Only PENDING/SCHEDULED jobs can be cancelled.",
        )

    job.status = JobStatus.FAILED.value
    job.error_message = "Cancelled by user"
    await db.commit()
