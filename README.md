# Job Scheduler

A multithreaded job scheduling system with pluggable scheduling policies, built with Python, FastAPI, PostgreSQL, and Redis.

Jobs are submitted via REST API, ordered by a configurable scheduling engine (FCFS, SJF, Priority, Round Robin), and executed concurrently in a thread pool with retry logic and a dead-letter queue for failed jobs.

## Architecture

```
                         ┌──────────────┐
                         │  curl / CLI  │
                         └──────┬───────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │     FastAPI REST API     │
                  │  POST/GET/DELETE /jobs   │
                  │  PUT /scheduler/policy   │
                  └─────┬───────────┬───────┘
                        │           │
                        ▼           ▼
               ┌────────────┐ ┌──────────┐
               │ PostgreSQL │ │  Redis   │
               │ (job store)│ │ (queue)  │
               └─────┬──────┘ └────┬─────┘
                     │              │
                     ▼              ▼
              ┌──────────────────────────────┐
              │      Scheduler Engine        │
              │  FCFS │ SJF │ Priority │ RR  │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   Worker Pool (4 threads)    │
              ├────────┬────────┬────────────┤
              │Thread 1│Thread 2│  Thread N  │
              └────────┴────────┴────────────┘
                  │         │         │
                  ▼         ▼         ▼
              WordCount  Thumbnail  Sleep
                Job        Job       Job

         On failure (retries exhausted):
              └──► Dead Letter Queue (Redis)
```

**API** and **Worker** run as separate processes (separate Docker containers), connected through PostgreSQL and Redis.

## Scheduling Policies

| Policy | Algorithm | Data Structure | Best For |
|--------|-----------|---------------|----------|
| **FCFS** | First Come First Served | `deque` (FIFO) | Fairness — no job gets starved |
| **SJF** | Shortest Job First | `heapq` (min-heap by duration) | Minimizing average wait time |
| **Priority** | Priority Queue | `heapq` (min-heap by priority) | Urgent jobs first (1=highest) |
| **Round Robin** | Time-sliced rotation | `deque` with requeue | Fair CPU sharing |

Policies can be **switched at runtime** via `PUT /scheduler/policy` — no restart needed.

## Job Lifecycle

```
PENDING → SCHEDULED → RUNNING → COMPLETED
                         │
                         ├──→ RETRIED → PENDING (retry loop)
                         │
                         └──→ FAILED → Dead Letter Queue
```

## Quick Start

**Prerequisites:** Docker and Docker Compose

```bash
# Clone and start everything
git clone https://github.com/srivatsav09/JobScheduler.git
cd JobScheduler
docker compose up --build

# In another terminal — submit a job
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Hello world", "job_type": "sleep", "payload": {"duration": 3}}'

# Check job status
curl http://localhost:8000/jobs/stats

# Switch to Priority scheduling
curl -X PUT http://localhost:8000/scheduler/policy \
  -H "Content-Type: application/json" \
  -d '{"policy": "priority"}'

# View Swagger docs
open http://localhost:8000/docs
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs/` | Submit a new job |
| `GET` | `/jobs/` | List jobs (filter by status/type, paginated) |
| `GET` | `/jobs/stats` | Aggregate statistics |
| `GET` | `/jobs/{id}` | Get a single job |
| `DELETE` | `/jobs/{id}` | Cancel a pending/scheduled job |
| `PUT` | `/scheduler/policy` | Switch scheduling policy at runtime |
| `GET` | `/scheduler/status` | Current policy, queue depth |
| `GET` | `/scheduler/dead-letter` | List permanently failed jobs |
| `GET` | `/health` | Postgres + Redis connectivity check |

## Job Types

### Sleep (simulated workload)
```json
{"name": "Task", "job_type": "sleep", "payload": {"duration": 5.0, "fail_probability": 0.3}}
```
Configurable `fail_probability` for testing retry and dead-letter queue behavior.

### Word Count (file I/O)
```json
{"name": "Count", "job_type": "word_count", "payload": {"file_path": "/data/sample.txt"}}
```
Returns `word_count`, `line_count`, `char_count`.

### Thumbnail (image processing)
```json
{"name": "Resize", "job_type": "thumbnail", "payload": {"input_path": "/data/sample.jpg", "width": 128, "height": 128}}
```
Generates a resized image using Pillow. Preserves aspect ratio.

## Project Structure

```
├── api/                    # FastAPI REST API
│   ├── routers/            #   Endpoint handlers (jobs, scheduler, health)
│   └── schemas/            #   Pydantic request/response models
├── scheduler/              # Scheduling engine
│   ├── base.py             #   AbstractScheduler interface
│   ├── fcfs.py             #   First Come First Served
│   ├── sjf.py              #   Shortest Job First
│   ├── priority.py         #   Priority Queue
│   ├── round_robin.py      #   Round Robin
│   ├── registry.py         #   Policy factory
│   └── engine.py           #   Orchestrator (DB → policy → Redis)
├── worker/                 # Multithreaded worker pool
│   ├── pool.py             #   ThreadPoolExecutor + Redis BLPOP
│   ├── executor.py         #   Single job lifecycle execution
│   ├── retry.py            #   Retry logic + dead-letter queue
│   └── main.py             #   Worker process entry point
├── jobs/                   # Job type implementations
│   ├── sleep_job.py        #   Simulated workload
│   ├── word_count.py       #   File word count
│   └── thumbnail.py        #   Image thumbnail generation
├── models/                 # SQLAlchemy ORM models
├── config/                 # Centralized configuration
├── tests/                  # 55 tests (pytest)
├── benchmarks/             # Throughput measurement per policy
├── docker-compose.yml      # Postgres + Redis + API + Worker
└── Dockerfile
```

## Running Tests

Tests use SQLite in-memory and fakeredis — no Docker needed.

```bash
pip install -r requirements.txt
pytest tests/ -v
```

```
55 passed in 2.00s
```

## Benchmarking

Measures jobs/sec under each scheduling policy:

```bash
# Start services first
docker compose up -d --build

# Run benchmark
python -m benchmarks.run_benchmark --policy all --num-jobs 100
```

```
Policy           Time (s)      Throughput
------------------------------------------
fcfs                0.515        97.09 j/s
sjf                 0.515        97.09 j/s
priority            0.531        94.16 j/s
round_robin         0.515        97.09 j/s
```

> Measured with 50 jobs × 10ms sleep on 4 worker threads (Docker, Windows 11).

## Design Decisions

- **Strategy pattern for schedulers**: `AbstractScheduler` base class with 4 implementations. Adding a new policy = implement the interface + register it.
- **In-memory scheduling, Redis as transport**: Policies use pure Python data structures (deque, heapq), making them unit-testable with zero infrastructure. Redis is only for inter-process communication.
- **Runtime policy switching**: Active policy stored in Redis key. Scheduler engine reads it every tick. `PUT /scheduler/policy` changes behavior without restart.
- **Separate API + Worker processes**: Scale independently. API handles HTTP, workers handle execution. Mirrors production architecture.
- **Retry via state machine**: Failed jobs go back to PENDING — the normal scheduler picks them up again. No separate retry queue needed.

## Tech Stack

- **Python 3.12** — FastAPI, SQLAlchemy 2.0, redis-py
- **PostgreSQL 16** — persistent job storage with JSON columns
- **Redis 7** — inter-process job queue + runtime config
- **Docker Compose** — one-command infrastructure setup