"""
Shared enumerations used across the entire project.

Using Python enums (inheriting from str) means:
- They serialize to JSON automatically ("PENDING", not "JobStatus.PENDING")
- They work as SQLAlchemy column values
- They work as FastAPI query parameters
- Typos become immediate errors instead of silent bugs
"""

import enum


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"        # job submitted, waiting to be scheduled
    SCHEDULED = "SCHEDULED"    # scheduler picked it up, placed in ready queue
    RUNNING = "RUNNING"        # worker is actively executing it
    COMPLETED = "COMPLETED"    # finished successfully
    FAILED = "FAILED"          # exhausted all retries, moved to dead-letter queue
    RETRIED = "RETRIED"        # failed but will be retried (transient state)


class JobType(str, enum.Enum):
    WORD_COUNT = "word_count"  # count words/lines/chars in a text file
    THUMBNAIL = "thumbnail"    # generate image thumbnail via Pillow
    SLEEP = "sleep"            # simulated workload (configurable duration + failure)


class SchedulingPolicy(str, enum.Enum):
    FCFS = "fcfs"              # First Come First Served — simple FIFO
    SJF = "sjf"                # Shortest Job First — min-heap by estimated_duration
    PRIORITY = "priority"      # Priority Queue — min-heap by priority (1 = highest)
    ROUND_ROBIN = "round_robin"  # Round Robin — time-sliced fairness
