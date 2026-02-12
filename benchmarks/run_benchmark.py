"""
CLI entry point for running throughput benchmarks.

Usage:
    python -m benchmarks.run_benchmark                          # all policies, 100 jobs
    python -m benchmarks.run_benchmark --policy fcfs            # single policy
    python -m benchmarks.run_benchmark --num-jobs 500           # more jobs
    python -m benchmarks.run_benchmark --policy all --num-jobs 200

Prerequisites:
    docker compose up (API + worker must be running)
"""

import argparse
import json

from benchmarks.throughput import ThroughputBenchmark


def main():
    parser = argparse.ArgumentParser(description="Job Scheduler Throughput Benchmark")
    parser.add_argument(
        "--num-jobs", type=int, default=100,
        help="Number of jobs to submit (default: 100)",
    )
    parser.add_argument(
        "--policy", type=str, default="all",
        choices=["fcfs", "sjf", "priority", "round_robin", "all"],
        help="Which policy to benchmark (default: all)",
    )
    parser.add_argument(
        "--base-url", type=str, default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    print(f"=== Job Scheduler Throughput Benchmark ===")
    print(f"Jobs: {args.num_jobs} | Policy: {args.policy}\n")

    bench = ThroughputBenchmark(base_url=args.base_url, num_jobs=args.num_jobs)

    if args.policy == "all":
        results = bench.run_all_policies()
    else:
        results = [bench.run(args.policy)]

    print("\n=== RESULTS ===")
    print(json.dumps(results, indent=2))

    # Summary table
    print("\n{:<15} {:>10} {:>15}".format("Policy", "Time (s)", "Throughput"))
    print("-" * 42)
    for r in results:
        print("{:<15} {:>10.3f} {:>12.2f} j/s".format(
            r["policy"], r["wall_clock_sec"], r["throughput_jobs_per_sec"]
        ))


if __name__ == "__main__":
    main()
