#!/bin/bash
# ============================================================
# Job Scheduler Demo Script
#
# Prerequisites: Docker + Docker Compose installed
# Usage: bash scripts/demo.sh
# ============================================================
set -e

API="http://localhost:8000"

echo "============================================"
echo "       Job Scheduler — Full Demo"
echo "============================================"

echo ""
echo "[1/8] Starting services (Postgres, Redis, API, Worker)..."
docker compose up -d --build
echo "      Waiting for services to be ready..."
sleep 8

echo ""
echo "[2/8] Health check..."
curl -s "$API/health" | python -m json.tool

echo ""
echo "[3/8] Current scheduler status (default: FCFS)..."
curl -s "$API/scheduler/status" | python -m json.tool

echo ""
echo "[4/8] Submitting a word count job..."
curl -s -X POST "$API/jobs/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Count words", "job_type": "word_count", "priority": 2, "payload": {"file_path": "/data/sample.txt"}}' \
  | python -m json.tool

echo ""
echo "[5/8] Submitting sleep jobs with different priorities..."
for i in 1 3 5 7; do
  curl -s -X POST "$API/jobs/" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Task priority=$i\", \"job_type\": \"sleep\", \"priority\": $i, \"estimated_duration\": $i.0, \"payload\": {\"duration\": 2}}" \
    > /dev/null
  echo "      Submitted: priority=$i"
done

echo ""
echo "[6/8] Submitting a job that will ALWAYS fail (demos retry + DLQ)..."
curl -s -X POST "$API/jobs/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Guaranteed failure", "job_type": "sleep", "max_retries": 2, "payload": {"duration": 0.1, "fail_probability": 1.0}}' \
  | python -m json.tool

echo ""
echo "[7/8] Switching scheduler to Priority Queue..."
curl -s -X PUT "$API/scheduler/policy" \
  -H "Content-Type: application/json" \
  -d '{"policy": "priority"}' \
  | python -m json.tool

echo ""
echo "      Waiting 15 seconds for jobs to complete..."
sleep 15

echo ""
echo "[8/8] Final results..."
echo ""
echo "--- Job Statistics ---"
curl -s "$API/jobs/stats" | python -m json.tool

echo ""
echo "--- Dead Letter Queue ---"
curl -s "$API/scheduler/dead-letter" | python -m json.tool

echo ""
echo "--- All Jobs ---"
curl -s "$API/jobs/?page_size=50" | python -m json.tool

echo ""
echo "============================================"
echo "  Demo complete!"
echo ""
echo "  Explore:"
echo "    Swagger docs:  $API/docs"
echo "    Job stats:     curl $API/jobs/stats"
echo "    Switch policy: curl -X PUT $API/scheduler/policy -d '{\"policy\":\"sjf\"}'"
echo "    Stop:          docker compose down"
echo "============================================"