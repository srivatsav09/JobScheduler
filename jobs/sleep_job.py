"""
Simulated workload job.

This is the most useful job type for demos and testing because:
- You control exactly how long it takes (duration parameter)
- You control whether it fails (fail_probability parameter)

Example payloads:
    {"duration": 3.0}                          → sleeps 3 seconds, always succeeds
    {"duration": 1.0, "fail_probability": 0.5} → sleeps 1 second, fails 50% of the time
    {"duration": 0.1, "fail_probability": 1.0} → fails immediately (demo dead-letter queue)

The fail_probability feature lets you demo the entire retry → dead-letter
pipeline on demand during an interview, without needing to create actual
error conditions.
"""

import time
import random

from jobs.base import AbstractJobHandler


class SleepJob(AbstractJobHandler):

    def run(self, payload: dict) -> dict:
        duration = payload.get("duration", 1.0)
        fail_probability = payload.get("fail_probability", 0.0)

        # Check for simulated failure BEFORE sleeping
        # (no point sleeping 30 seconds just to fail)
        if random.random() < fail_probability:
            raise RuntimeError(
                f"Simulated failure (fail_probability={fail_probability})"
            )

        time.sleep(duration)

        return {
            "slept_for": duration,
            "message": f"Completed sleep of {duration}s",
        }

    @property
    def job_type(self) -> str:
        return "sleep"
