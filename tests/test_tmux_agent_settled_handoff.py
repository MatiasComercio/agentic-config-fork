#!/usr/bin/env python3
"""Static contract checks for tmux-agent settled handoff semantics."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMUX_AGENT_EXTENSION = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "index.ts"
TMUX_AGENT_SOURCE = TMUX_AGENT_EXTENSION.read_text()


def test_report_parent_surface_includes_explicit_closeout_kind() -> None:
    """The child report_parent surface should expose explicit closeout declarations."""
    assert 'type ReportParentKind = "question" | "blocker" | "progress" | "failure" | "closeout";' in TMUX_AGENT_SOURCE
    assert 'StringEnum(["question", "blocker", "progress", "failure", "closeout"] as const)' in TMUX_AGENT_SOURCE
    assert "reportKind: question | blocker | progress | failure | closeout" in TMUX_AGENT_SOURCE


def test_runtime_no_longer_synthesizes_success_from_agent_end_or_quiet_time() -> None:
    """Success should not come from agent_end snapshots, quiet time, or shutdown synthesis."""
    assert "TERMINAL_COMPLETION_SETTLE_MS" not in TMUX_AGENT_SOURCE
    assert 'pi.on("agent_end"' not in TMUX_AGENT_SOURCE
    assert "flushPendingTerminalReport" not in TMUX_AGENT_SOURCE
    assert "getLastBridgeActivityTimestamp" not in TMUX_AGENT_SOURCE
    assert "Child exited without a valid terminal declaration." in TMUX_AGENT_SOURCE


def test_status_surface_exposes_settled_state_and_protocol_violation() -> None:
    """Status/report surfaces should expose explicit settled states."""
    for state in (
        "running",
        "settled_completion",
        "settled_failure",
        "settled_blocked",
        "settled_waiting_on_parent",
        "protocol_violation",
    ):
        assert state in TMUX_AGENT_SOURCE
    assert "bridgeSettlementState:" in TMUX_AGENT_SOURCE
    assert "bridgeProtocolViolationReason:" in TMUX_AGENT_SOURCE


def test_progress_is_non_follow_up_by_default_and_closeout_is_non_terminal_until_exit() -> None:
    """Progress should stay bounded while closeout waits for settlement."""
    trigger_fn_match = re.search(
        r"function shouldTriggerTurnForEvent\(event: BridgeEvent, launch: BridgeLaunchFile\): boolean \{(?P<body>.*?)\n\}",
        TMUX_AGENT_SOURCE,
        flags=re.DOTALL,
    )
    assert trigger_fn_match is not None
    trigger_body = trigger_fn_match.group("body")
    assert 'if (event.type === "closeout") return false;' in trigger_body
    assert 'if (event.type === "progress") return Boolean(event.requiresResponse);' in trigger_body

    settled_trigger_match = re.search(
        r"function shouldTriggerTurnForSettledState\(state: SettledTerminalState, launch: BridgeLaunchFile\): boolean \{(?P<body>.*?)\n\}",
        TMUX_AGENT_SOURCE,
        flags=re.DOTALL,
    )
    assert settled_trigger_match is not None
    settled_trigger_body = settled_trigger_match.group("body")
    assert 'if (state === "settled_completion") return launch.notificationMode === "notify-and-follow-up";' in settled_trigger_body


def test_settlement_evaluation_covers_closeout_and_protocol_violations() -> None:
    """Settlement state machine should handle success and non-success terminal branches honestly."""
    assert "function evaluateBridgeSettlement(events: BridgeEvent[]): BridgeSettlementEvaluation" in TMUX_AGENT_SOURCE
    assert "Multiple closeout declarations were emitted." in TMUX_AGENT_SOURCE
    assert "Post-closeout child report detected:" in TMUX_AGENT_SOURCE
    assert "settled_waiting_on_parent" in TMUX_AGENT_SOURCE
    assert "const requiresResponse = request.kind === \"closeout\" ? false" in TMUX_AGENT_SOURCE
