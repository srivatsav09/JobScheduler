"""Tests for the SleepJob handler."""

import pytest
from jobs.sleep_job import SleepJob


def test_sleep_completes_with_result():
    handler = SleepJob()
    result = handler.run({"duration": 0.01})  # very short sleep for fast tests

    assert result["slept_for"] == 0.01
    assert "Completed" in result["message"]


def test_sleep_default_duration():
    handler = SleepJob()
    result = handler.run({})  # no duration → defaults to 1.0

    assert result["slept_for"] == 1.0


def test_guaranteed_failure():
    """fail_probability=1.0 should always raise."""
    handler = SleepJob()
    with pytest.raises(RuntimeError, match="Simulated failure"):
        handler.run({"duration": 0.01, "fail_probability": 1.0})


def test_guaranteed_success():
    """fail_probability=0.0 should never raise."""
    handler = SleepJob()
    # Run multiple times to increase confidence
    for _ in range(10):
        result = handler.run({"duration": 0.01, "fail_probability": 0.0})
        assert result["slept_for"] == 0.01


def test_job_type():
    assert SleepJob().job_type == "sleep"
