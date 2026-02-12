"""
Job handler registry — maps job_type strings to handler instances.

When a worker pulls a job from Redis, it knows the job_type ("sleep",
"word_count", "thumbnail") but needs the actual handler class to execute it.
This registry does that lookup.

Same pattern as scheduler/registry.py — one place that knows all the types.
"""

from jobs.base import AbstractJobHandler
from jobs.word_count import WordCountJob
from jobs.thumbnail import ThumbnailJob
from jobs.sleep_job import SleepJob

# Each handler is instantiated once and reused (they're stateless)
_REGISTRY: dict[str, AbstractJobHandler] = {}


def _register_defaults() -> None:
    for handler_cls in [WordCountJob, ThumbnailJob, SleepJob]:
        handler = handler_cls()
        _REGISTRY[handler.job_type] = handler


_register_defaults()


def get_job_handler(job_type: str) -> AbstractJobHandler:
    """Look up a handler by job_type string. Raises ValueError if unknown."""
    handler = _REGISTRY.get(job_type)
    if handler is None:
        raise ValueError(
            f"Unknown job type: '{job_type}'. Available: {list(_REGISTRY.keys())}"
        )
    return handler
