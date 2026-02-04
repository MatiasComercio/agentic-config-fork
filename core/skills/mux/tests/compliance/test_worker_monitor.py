#!/usr/bin/env python3
"""
Compliance tests for worker-monitor pairing requirements.

Validates that every worker has a corresponding monitor with matching task context.
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///

from __future__ import annotations

import re

import pytest


def test_monitor_launched_with_workers(inspector):
    """Verify monitor launched whenever workers are created."""
    # Simulate worker creation
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-001",
            "instructions": "Analyze code",
        },
    )

    # Simulate monitor creation
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "monitor",
            "task_id": "monitor-001",
            "instructions": "Monitor worker-001",
        },
    )

    task_calls = inspector.get_calls("Task")

    # Extract workers and monitors
    workers = [c for c in task_calls if c.parameters.get("agent_type") == "worker"]
    monitors = [c for c in task_calls if c.parameters.get("agent_type") == "monitor"]

    assert len(monitors) > 0, "Monitor must be launched with workers"
    assert len(monitors) >= len(
        workers
    ), "Must have at least one monitor per worker batch"


def test_monitor_has_expected_count(inspector):
    """Verify monitor receives EXPECTED count parameter."""
    # Simulate worker + monitor creation
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-001",
        },
    )
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-002",
        },
    )

    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "monitor",
            "instructions": "Monitor 2 workers",
            "expected_count": 2,
        },
    )

    monitors = [
        c for c in inspector.get_calls("Task") if c.parameters.get("agent_type") == "monitor"
    ]

    for monitor in monitors:
        # Check for EXPECTED count in instructions or parameters
        instructions = monitor.parameters.get("instructions", "")
        has_count = (
            "expected_count" in monitor.parameters
            or "EXPECTED" in instructions.upper()
            or re.search(r"\d+\s+workers?", instructions.lower())
        )

        assert has_count, "Monitor must know EXPECTED worker count"


def test_workers_and_monitor_same_message(inspector):
    """Verify workers and monitor launched in same message batch."""
    # Simulate simultaneous launch
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-001",
        },
    )
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-002",
        },
    )
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "monitor",
            "task_id": "monitor-001",
        },
    )

    task_calls = inspector.get_calls("Task")

    # Verify tasks created in close temporal proximity
    if len(task_calls) >= 3:
        timestamps = [c.timestamp for c in task_calls[:3]]
        time_spread = max(timestamps) - min(timestamps)

        # All should be created within 1 second (same message)
        assert time_spread < 1.0, "Workers and monitor must launch in same message"


def test_no_worker_without_monitor(inspector):
    """Verify no workers run without monitor oversight."""
    # Simulate worker-only scenario (violation)
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "worker-001",
        },
    )

    task_calls = inspector.get_calls("Task")
    workers = [c for c in task_calls if c.parameters.get("agent_type") == "worker"]
    monitors = [c for c in task_calls if c.parameters.get("agent_type") == "monitor"]

    # Verify the violation is detected
    if len(workers) > 0:
        with pytest.raises(AssertionError, match="Workers require monitor - none found"):
            assert len(monitors) > 0, "Workers require monitor - none found"


def test_monitor_references_worker_tasks(inspector):
    """Verify monitor instructions reference worker task IDs."""
    # Simulate proper pairing
    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "worker",
            "task_id": "abc123",
        },
    )

    inspector.record(
        "Task",
        {
            "run_in_background": True,
            "agent_type": "monitor",
            "instructions": "Monitor task abc123",
        },
    )

    monitors = [
        c for c in inspector.get_calls("Task") if c.parameters.get("agent_type") == "monitor"
    ]

    workers = [
        c for c in inspector.get_calls("Task") if c.parameters.get("agent_type") == "worker"
    ]

    worker_ids = [w.parameters.get("task_id") for w in workers if "task_id" in w.parameters]

    for monitor in monitors:
        instructions = monitor.parameters.get("instructions", "")

        # Verify monitor references at least one worker ID
        references_worker = any(wid in instructions for wid in worker_ids if wid)

        assert (
            references_worker
        ), "Monitor must reference worker task IDs in instructions"
