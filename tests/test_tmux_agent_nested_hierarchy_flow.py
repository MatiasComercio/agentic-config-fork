#!/usr/bin/env python3
"""Scenario checks for nested tmux-agent hierarchy bridge settlement."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_RUNTIME = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "bridge-authority-runtime.ts"
SETTLEMENT_RUNTIME = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "settlement-runtime.ts"

NODE_RUNTIME_EVAL = """
import { pathToFileURL } from "node:url";

const authorityPath = process.argv[1];
const settlementPath = process.argv[2];
const payload = JSON.parse(process.argv[3]);
const authority = await import(pathToFileURL(authorityPath).href);
const settlement = await import(pathToFileURL(settlementPath).href);

if (payload.action === "hierarchy-flow") {
	const binding = authority.bindBridgeAuthoritativeSession(payload.headSession);
	const headAuthority = authority.evaluateBridgeAuthority(binding, payload.headSession);
	const scoutAuthority = authority.evaluateBridgeAuthority(binding, payload.scoutSession);
	const scoutEvents = scoutAuthority.isAuthoritative ? payload.scoutTerminalEvents : [];
	const settlementBeforeHead = settlement.evaluateBridgeSettlement(scoutEvents);
	const headEvents = headAuthority.isAuthoritative ? payload.headTerminalEvents : [];
	const settlementAfterHead = settlement.evaluateBridgeSettlement([...scoutEvents, ...headEvents]);
	process.stdout.write(JSON.stringify({
		binding,
		headAuthority,
		scoutAuthority,
		settlementBeforeHead,
		settlementAfterHead,
	}));
	process.exit(0);
}

throw new Error(`Unsupported action: ${payload.action}`);
""".strip()


def run_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the combined hierarchy scenario through Node and parse JSON output."""
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--input-type=module",
            "--eval",
            NODE_RUNTIME_EVAL,
            str(AUTHORITY_RUNTIME),
            str(SETTLEMENT_RUNTIME),
            json.dumps(payload),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Node hierarchy runtime execution failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def session_identity(*, session_key: str, session_file: str, leaf_id: str, process_id: int) -> dict[str, Any]:
    """Build a synthetic runtime session identity payload."""
    return {
        "sessionKey": session_key,
        "sessionFile": session_file,
        "leafId": leaf_id,
        "processId": process_id,
    }


def event(event_id: str, event_type: str, *, direction: str) -> dict[str, Any]:
    """Build a synthetic bridge event payload."""
    return {
        "eventId": event_id,
        "direction": direction,
        "type": event_type,
    }


def test_two_level_tmux_hierarchy_ignores_local_helper_completion_until_head_finishes() -> None:
    """Chief->Head bridge should settle only when Head finishes, not when Head's local scout helper ends."""
    result = run_runtime(
        {
            "action": "hierarchy-flow",
            "headSession": session_identity(
                session_key="head-session-key",
                session_file="/tmp/head-session.json",
                leaf_id="head-leaf",
                process_id=101,
            ),
            "scoutSession": session_identity(
                session_key="head-session-key",
                session_file="/tmp/head-session.json",
                leaf_id="scout-leaf",
                process_id=202,
            ),
            "scoutTerminalEvents": [
                event("scout-closeout", "closeout", direction="child_to_parent"),
                event("scout-exited", "exited", direction="system"),
            ],
            "headTerminalEvents": [
                event("head-closeout", "closeout", direction="child_to_parent"),
                event("head-exited", "exited", direction="system"),
            ],
        }
    )

    assert result["headAuthority"] == {"isAuthoritative": True}
    assert result["scoutAuthority"] == {
        "isAuthoritative": False,
        "reason": "Bridge is bound to leaf head-leaf, current leaf is scout-leaf.",
    }
    assert result["settlementBeforeHead"] == {"settledState": "running"}
    assert result["settlementAfterHead"]["settledState"] == "settled_completion"
    assert result["settlementAfterHead"]["terminalEvent"]["eventId"] == "head-closeout"
