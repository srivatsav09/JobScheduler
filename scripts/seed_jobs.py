"""
Seed script — submits a variety of sample jobs for demo purposes.

Usage:
    python -m scripts.seed_jobs

This creates:
- 1 word count job (real file I/O)
- 1 thumbnail job (real image processing)
- 3 sleep jobs with different priorities and durations
- 1 guaranteed-failure job (demos retry + dead-letter queue)

Run this after `docker compose up` to populate the system with demo data.
"""

import httpx

BASE_URL = "http://localhost:8000"


def seed():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    jobs = [
        {
            "name": "Count words in sample.txt",
            "job_type": "word_count",
            "priority": 2,
            "estimated_duration": 0.5,
            "payload": {"file_path": "/data/sample.txt"},
        },
        {
            "name": "Generate thumbnail",
            "job_type": "thumbnail",
            "priority": 3,
            "estimated_duration": 1.0,
            "payload": {
                "input_path": "/data/sample.jpg",
                "output_path": "/data/sample_thumb.jpg",
                "width": 128,
                "height": 128,
            },
        },
        {
            "name": "Quick background task",
            "job_type": "sleep",
            "priority": 1,
            "estimated_duration": 2.0,
            "payload": {"duration": 2.0},
        },
        {
            "name": "Normal priority task",
            "job_type": "sleep",
            "priority": 5,
            "estimated_duration": 5.0,
            "payload": {"duration": 5.0},
        },
        {
            "name": "Low priority report",
            "job_type": "sleep",
            "priority": 9,
            "estimated_duration": 8.0,
            "payload": {"duration": 8.0},
        },
        {
            "name": "Flaky job (will fail and retry)",
            "job_type": "sleep",
            "priority": 5,
            "max_retries": 2,
            "payload": {"duration": 0.1, "fail_probability": 1.0},
        },
    ]

    print(f"Submitting {len(jobs)} jobs to {BASE_URL}...\n")

    for job in jobs:
        resp = client.post("/jobs/", json=job)
        resp.raise_for_status()
        data = resp.json()
        print(f"  [{data['status']}] {data['name']} (id: {data['id'][:8]}...)")

    print("\nDone! Jobs are now flowing through the scheduler.")
    print("Check status:  curl http://localhost:8000/jobs/stats")
    print("List jobs:     curl http://localhost:8000/jobs/")


if __name__ == "__main__":
    seed()