#!/usr/bin/env python3
"""Behavior checks for tmux-agent settlement and parent-delivery decisions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTLEMENT_RUNTIME = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "settlement-runtime.ts"

NODE_RUNTIME_EVAL = """
import { pathToFileURL } from "node:url";

const helperPath = process.argv[1];
const payload = JSON.parse(process.argv[2]);
const runtime = await import(pathToFileURL(helperPath).href);

if (payload.action === "evaluate") {
	process.stdout.write(JSON.stringify(runtime.evaluateBridgeSettlement(payload.events)));
	process.exit(0);
}

if (payload.action === "delivery") {
	process.stdout.write(JSON.stringify({
		deliver: runtime.shouldDeliverBridgeEventToParent(payload.event),
		trigger: runtime.shouldTriggerTurnForEvent(payload.event, payload.launch),
	}));
	process.exit(0);
}

if (payload.action === "settled-trigger") {
	process.stdout.write(JSON.stringify({
		trigger: runtime.shouldTriggerTurnForSettledState(payload.state, payload.launch),
	}));
	process.exit(0);
}

throw new Error(`Unsupported action: ${payload.action}`);
""".strip()


def run_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the package-local runtime helper through Node and parse JSON output."""
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--input-type=module",
            "--eval",
            NODE_RUNTIME_EVAL,
            str(SETTLEMENT_RUNTIME),
            json.dumps(payload),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Node runtime helper execution failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as error:  # pragma: no cover - assertion helper
        raise AssertionError(f"Expected JSON output.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}") from error
    assert isinstance(parsed, dict)
    return parsed


def event(
    event_id: str,
    event_type: str,
    *,
    direction: str = "child_to_parent",
    requires_response: bool | None = None,
) -> dict[str, Any]:
    """Build a synthetic bridge event payload used by helper behavior tests."""
    payload: dict[str, Any] = {
        "eventId": event_id,
        "direction": direction,
        "type": event_type,
    }
    if requires_response is not None:
        payload["requiresResponse"] = requires_response
    return payload


def test_settlement_waits_for_exit_even_when_closeout_exists() -> None:
    """A closeout declaration is non-terminal until the child actually exits."""
    result = run_runtime({"action": "evaluate", "events": [event("closeout-1", "closeout")]})
    assert result["settledState"] == "running"


def test_settlement_completes_only_after_closeout_and_exit() -> None:
    """Successful settlement should require closeout + explicit exit evidence."""
    result = run_runtime(
        {
            "action": "evaluate",
            "events": [
                event("closeout-1", "closeout"),
                event("exited-1", "exited", direction="system"),
            ],
        }
    )
    assert result["settledState"] == "settled_completion"
    terminal_event = result["terminalEvent"]
    assert isinstance(terminal_event, dict)
    assert terminal_event["eventId"] == "closeout-1"


def test_settlement_marks_undeclared_exit_as_protocol_violation() -> None:
    """Exit without a declared terminal report must not settle as success."""
    result = run_runtime({"action": "evaluate", "events": [event("exited-1", "exited", direction="system")]})
    assert result["settledState"] == "protocol_violation"
    assert result["protocolViolationReason"] == "Child exited without a valid terminal declaration."


def test_settlement_maps_declared_non_success_terminal_reports() -> None:
    """Declared non-success terminal reports should settle honestly after exit."""
    cases = [
        ("failure", "settled_failure"),
        ("blocker", "settled_blocked"),
        ("question", "settled_waiting_on_parent"),
    ]
    for terminal_type, expected_state in cases:
        result = run_runtime(
            {
                "action": "evaluate",
                "events": [
                    event("terminal-1", terminal_type),
                    event("exited-1", "exited", direction="system"),
                ],
            }
        )
        assert result["settledState"] == expected_state


def test_settlement_flags_closeout_sequence_protocol_violations() -> None:
    """Multiple closeouts or post-closeout reports should settle as protocol violations."""
    multiple_closeouts = run_runtime(
        {
            "action": "evaluate",
            "events": [
                event("closeout-1", "closeout"),
                event("closeout-2", "closeout"),
                event("exited-1", "exited", direction="system"),
            ],
        }
    )
    assert multiple_closeouts["settledState"] == "protocol_violation"
    assert multiple_closeouts["protocolViolationReason"] == "Multiple closeout declarations were emitted."

    post_closeout_report = run_runtime(
        {
            "action": "evaluate",
            "events": [
                event("closeout-1", "closeout"),
                event("progress-1", "progress"),
                event("exited-1", "exited", direction="system"),
            ],
        }
    )
    assert post_closeout_report["settledState"] == "protocol_violation"
    assert "Post-closeout child report detected: progress (progress-1)" == post_closeout_report["protocolViolationReason"]


def test_delivery_hides_closeout_until_settlement() -> None:
    """Closeout should not be parent-visible before settlement finalization."""
    decision = run_runtime(
        {
            "action": "delivery",
            "event": event("closeout-1", "closeout"),
            "launch": {"notificationMode": "notify-and-follow-up"},
        }
    )
    assert decision == {"deliver": False, "trigger": False}


def test_delivery_keeps_progress_non_follow_up_by_default() -> None:
    """Progress remains visible but should only trigger follow-up when requested."""
    default_progress = run_runtime(
        {
            "action": "delivery",
            "event": event("progress-1", "progress"),
            "launch": {"notificationMode": "notify-and-follow-up"},
        }
    )
    assert default_progress == {"deliver": True, "trigger": False}

    requested_progress = run_runtime(
        {
            "action": "delivery",
            "event": event("progress-2", "progress", requires_response=True),
            "launch": {"notificationMode": "notify-and-follow-up"},
        }
    )
    assert requested_progress == {"deliver": True, "trigger": True}


def test_settled_trigger_decisions_obey_notification_mode() -> None:
    """Settlement follow-up should respect completion vs non-success notification rules."""
    completion_notify = run_runtime(
        {
            "action": "settled-trigger",
            "state": "settled_completion",
            "launch": {"notificationMode": "notify"},
        }
    )
    assert completion_notify == {"trigger": False}

    completion_follow_up = run_runtime(
        {
            "action": "settled-trigger",
            "state": "settled_completion",
            "launch": {"notificationMode": "notify-and-follow-up"},
        }
    )
    assert completion_follow_up == {"trigger": True}

    failure_notify = run_runtime(
        {
            "action": "settled-trigger",
            "state": "settled_failure",
            "launch": {"notificationMode": "notify"},
        }
    )
    assert failure_notify == {"trigger": True}

    silent_failure = run_runtime(
        {
            "action": "settled-trigger",
            "state": "settled_failure",
            "launch": {"notificationMode": "silent"},
        }
    )
    assert silent_failure == {"trigger": False}
