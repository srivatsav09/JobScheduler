"""
API integration tests for /jobs endpoints.

These use the test HTTP client from conftest.py, which talks to
the FastAPI app with an in-memory SQLite DB and fake Redis.
No Docker, no network — runs in milliseconds.
"""

import pytest


@pytest.mark.asyncio
async def test_create_job(client):
    """POST /jobs/ should create a job and return it with status PENDING."""
    response = await client.post("/jobs/", json={
        "name": "test sleep",
        "job_type": "sleep",
        "priority": 3,
        "estimated_duration": 2.0,
        "payload": {"duration": 2.0},
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test sleep"
    assert data["job_type"] == "sleep"
    assert data["status"] == "PENDING"
    assert data["priority"] == 3
    assert data["estimated_duration"] == 2.0
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_job_with_defaults(client):
    """Job with no priority/duration should use defaults (5 and 1.0)."""
    response = await client.post("/jobs/", json={
        "name": "minimal job",
        "job_type": "sleep",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == 5
    assert data["estimated_duration"] == 1.0
    assert data["max_retries"] == 3


@pytest.mark.asyncio
async def test_create_job_invalid_type(client):
    """Invalid job_type should return 422 validation error."""
    response = await client.post("/jobs/", json={
        "name": "bad job",
        "job_type": "nonexistent",
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_job_priority_out_of_range(client):
    """Priority outside 1-10 should return 422."""
    response = await client.post("/jobs/", json={
        "name": "bad priority",
        "job_type": "sleep",
        "priority": 99,
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_job_by_id(client):
    """GET /jobs/{id} should return the specific job."""
    # Create a job first
    create_response = await client.post("/jobs/", json={
        "name": "findable job",
        "job_type": "sleep",
    })
    job_id = create_response.json()["id"]

    # Fetch it
    response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["name"] == "findable job"


@pytest.mark.asyncio
async def test_get_nonexistent_job(client):
    """GET /jobs/{bad_id} should return 404."""
    response = await client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs(client):
    """GET /jobs/ should return paginated list."""
    # Create two jobs
    await client.post("/jobs/", json={"name": "job1", "job_type": "sleep"})
    await client.post("/jobs/", json={"name": "job2", "job_type": "sleep"})

    response = await client.get("/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["jobs"]) == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status(client):
    """GET /jobs/?status=PENDING should only return PENDING jobs."""
    await client.post("/jobs/", json={"name": "pending job", "job_type": "sleep"})

    response = await client.get("/jobs/?status=PENDING")
    assert response.status_code == 200
    for job in response.json()["jobs"]:
        assert job["status"] == "PENDING"


@pytest.mark.asyncio
async def test_cancel_pending_job(client):
    """DELETE /jobs/{id} should cancel a PENDING job."""
    create_response = await client.post("/jobs/", json={
        "name": "cancel me",
        "job_type": "sleep",
    })
    job_id = create_response.json()["id"]

    response = await client.delete(f"/jobs/{job_id}")
    assert response.status_code == 204

    # Verify it's now FAILED with cancel message
    get_response = await client.get(f"/jobs/{job_id}")
    assert get_response.json()["status"] == "FAILED"
    assert "Cancelled" in get_response.json()["error_message"]


@pytest.mark.asyncio
async def test_get_job_stats(client):
    """GET /jobs/stats should return aggregate counts."""
    await client.post("/jobs/", json={"name": "job1", "job_type": "sleep"})
    await client.post("/jobs/", json={"name": "job2", "job_type": "sleep"})

    response = await client.get("/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 2
    assert data["pending"] == 2
