"""
Throughput benchmark — measures jobs/sec under each scheduling policy.

How it works:
1. Set the scheduling policy via the API
2. Submit N short sleep jobs (0.01s each — fast enough to measure throughput)
3. Wait for all jobs to complete
4. Calculate: throughput = N / total_wall_clock_time

This gives you real numbers to cite in interviews:
"FCFS processes 45 jobs/sec, SJF processes 42 jobs/sec on 4 worker threads."

The jobs use tiny sleep durations so the bottleneck is the scheduling
and worker infrastructure, not the job itself. This measures system
throughput, not job execution time.
"""

import time

import httpx

from models.enums import SchedulingPolicy

BASE_URL = "http://localhost:8000"


class ThroughputBenchmark:

    def __init__(self, base_url: str = BASE_URL, num_jobs: int = 100):
        self.base_url = base_url
        self.num_jobs = num_jobs
        self.client = httpx.Client(timeout=30.0)

    def set_policy(self, policy: str) -> None:
        """Switch the active scheduling policy."""
        resp = self.client.put(
            f"{self.base_url}/scheduler/policy",
            json={"policy": policy},
        )
        resp.raise_for_status()

    def submit_jobs(self) -> list[str]:
        """Submit N sleep jobs with minimal duration for throughput testing."""
        job_ids = []
        for i in range(self.num_jobs):
            resp = self.client.post(
                f"{self.base_url}/jobs/",
                json={
                    "name": f"bench-{i}",
                    "job_type": "sleep",
                    "priority": (i % 10) + 1,             # spread across priorities
                    "estimated_duration": 0.01 * ((i % 5) + 1),  # vary for SJF
                    "payload": {"duration": 0.01},         # 10ms sleep — very fast
                },
            )
            resp.raise_for_status()
            job_ids.append(resp.json()["id"])
        return job_ids

    def _get_done_count(self) -> int:
        """Get current completed + failed count from the stats endpoint."""
        stats = self.client.get(f"{self.base_url}/jobs/stats").json()
        return stats["completed"] + stats["failed"]

    def wait_for_completion(self, baseline: int, timeout: float = 120.0) -> float:
        """
        Poll until (completed+failed) increases by num_jobs from baseline.

        baseline is the done count BEFORE we submitted jobs, so we only
        wait for our batch to finish — not jobs from previous runs.
        """
        start = time.monotonic()
        target = baseline + self.num_jobs
        while time.monotonic() - start < timeout:
            done = self._get_done_count()
            if done >= target:
                return time.monotonic() - start
            time.sleep(0.5)
        raise TimeoutError(f"Jobs didn't complete within {timeout}s")

    def run(self, policy: str) -> dict:
        """Run the benchmark for a single policy."""
        self.set_policy(policy)
        time.sleep(1)  # let policy propagate to scheduler engine

        # Snapshot done count BEFORE submitting so we only wait for our batch
        baseline = self._get_done_count()
        job_ids = self.submit_jobs()
        elapsed = self.wait_for_completion(baseline)
        throughput = self.num_jobs / elapsed

        return {
            "policy": policy,
            "num_jobs": self.num_jobs,
            "wall_clock_sec": round(elapsed, 3),
            "throughput_jobs_per_sec": round(throughput, 2),
        }

    def run_all_policies(self) -> list[dict]:
        """Benchmark all 4 policies sequentially."""
        results = []
        for policy in SchedulingPolicy:
            print(f"\n--- Benchmarking {policy.value} ---")
            result = self.run(policy.value)
            results.append(result)
            print(
                f"  {result['throughput_jobs_per_sec']} jobs/sec "
                f"({result['wall_clock_sec']}s wall clock)"
            )
            time.sleep(2)  # cooldown between policies
        return results
