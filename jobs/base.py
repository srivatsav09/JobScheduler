"""
Abstract base class for job handlers.

Each job type (sleep, word_count, thumbnail) implements this interface.
The worker calls handler.run(payload) without knowing which type it is —
it looks up the handler from the registry by job_type string.

Same Strategy pattern as the schedulers:
- AbstractJobHandler = interface
- SleepJob, WordCountJob, ThumbnailJob = implementations
- registry.py = factory lookup

To add a new job type:
1. Create a class that inherits AbstractJobHandler
2. Implement run() and job_type
3. Add it to the registry
"""

from abc import ABC, abstractmethod


class AbstractJobHandler(ABC):

    @abstractmethod
    def run(self, payload: dict) -> dict:
        """
        Execute the job.

        Args:
            payload: job-specific parameters from the database JSONB column.
                     Each job type expects different keys in here.

        Returns:
            dict with results — stored in the Job.result JSONB column.

        Raises:
            Any exception → triggers retry logic in the worker.
        """
        ...

    @property
    @abstractmethod
    def job_type(self) -> str:
        """Unique identifier matching JobType enum (e.g., 'sleep', 'word_count')."""
        ...
