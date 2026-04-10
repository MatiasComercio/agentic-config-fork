#!/usr/bin/env python3
"""Behavior and wiring checks for tmux-agent bridge authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_RUNTIME = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "bridge-authority-runtime.ts"
TMUX_AGENT_EXTENSION = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "index.ts"
TMUX_AGENT_SOURCE = TMUX_AGENT_EXTENSION.read_text()

NODE_RUNTIME_EVAL = """
import { pathToFileURL } from "node:url";

const helperPath = process.argv[1];
const payload = JSON.parse(process.argv[2]);
const runtime = await import(pathToFileURL(helperPath).href);

if (payload.action === "bind") {
	process.stdout.write(JSON.stringify(runtime.bindBridgeAuthoritativeSession(payload.current)));
	process.exit(0);
}

if (payload.action === "evaluate") {
	process.stdout.write(JSON.stringify(runtime.evaluateBridgeAuthority(payload.binding, payload.current)));
	process.exit(0);
}

throw new Error(`Unsupported action: ${payload.action}`);
""".strip()


def run_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the authority helper through Node and parse the JSON output."""
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--input-type=module",
            "--eval",
            NODE_RUNTIME_EVAL,
            str(AUTHORITY_RUNTIME),
            json.dumps(payload),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Node authority helper execution failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def session_identity(
    *,
    session_key: str = "session-key-1",
    session_file: str | None = "/tmp/child-session.json",
    leaf_id: str | None = "leaf-1",
    process_id: int = 101,
) -> dict[str, Any]:
    """Build a synthetic runtime session identity payload."""
    payload: dict[str, Any] = {
        "sessionKey": session_key,
        "processId": process_id,
    }
    if session_file is not None:
        payload["sessionFile"] = session_file
    if leaf_id is not None:
        payload["leafId"] = leaf_id
    return payload


def test_binding_captures_authoritative_child_identity() -> None:
    """The first direct tmux child binding should preserve its session identity."""
    identity = session_identity()
    result = run_runtime({"action": "bind", "current": identity})
    assert result == {
        "authoritativeSessionKey": "session-key-1",
        "authoritativeSessionFile": "/tmp/child-session.json",
        "authoritativeLeafId": "leaf-1",
        "authoritativeProcessId": 101,
    }


def test_unbound_bridge_is_not_authoritative() -> None:
    """An unbound bridge should fail closed until the direct child claims it."""
    result = run_runtime({"action": "evaluate", "binding": {}, "current": session_identity()})
    assert result == {
        "isAuthoritative": False,
        "reason": "No authoritative tmux-agent child session has been bound to this bridge yet.",
    }


def test_exact_bound_child_is_authoritative() -> None:
    """The bound direct child identity should evaluate as authoritative."""
    identity = session_identity()
    binding = run_runtime({"action": "bind", "current": identity})
    result = run_runtime({"action": "evaluate", "binding": binding, "current": identity})
    assert result == {"isAuthoritative": True}


def test_nested_helper_is_rejected_when_leaf_differs() -> None:
    """A nested helper sharing bridge env but running on another leaf must be rejected."""
    binding = run_runtime({"action": "bind", "current": session_identity(leaf_id="head-leaf", process_id=111)})
    nested_helper = session_identity(leaf_id="scout-leaf", process_id=222)
    result = run_runtime({"action": "evaluate", "binding": binding, "current": nested_helper})
    assert result == {
        "isAuthoritative": False,
        "reason": "Bridge is bound to leaf head-leaf, current leaf is scout-leaf.",
    }


def test_process_id_is_used_as_fallback_when_leaf_is_missing() -> None:
    """Without leaf identity, a different nested process should still be rejected."""
    bound_without_leaf = run_runtime(
        {
            "action": "bind",
            "current": session_identity(leaf_id=None, process_id=501),
        }
    )
    nested_helper = session_identity(leaf_id=None, process_id=777)
    result = run_runtime({"action": "evaluate", "binding": bound_without_leaf, "current": nested_helper})
    assert result == {
        "isAuthoritative": False,
        "reason": "Bridge is bound to process id 501, current process id is 777.",
    }


def test_extension_wires_authority_checks_into_bridge_lifecycle() -> None:
    """The extension should gate lifecycle hooks and reports on authoritative child ownership."""
    assert 'from "./bridge-authority-runtime"' in TMUX_AGENT_SOURCE
    assert 'await resolveBridgeAuthority(currentEnv.bridgeDir, ctx, { bindIfMissing: true })' in TMUX_AGENT_SOURCE
    assert 'const bridgeAuthority = await resolveBridgeAuthority(currentEnv.bridgeDir, ctx);' in TMUX_AGENT_SOURCE
    assert 'if (!bridgeAuthority.isAuthoritative) return;' in TMUX_AGENT_SOURCE
    assert 'report_parent is reserved for the authoritative tmux-agent session.' in TMUX_AGENT_SOURCE
    assert 'currentEnv.bridgeDir && currentEnv.launchId && currentEnv.agentId && bridgeAuthority?.isAuthoritative' in TMUX_AGENT_SOURCE
    assert 'Their completion does not report to the parent and does not justify closeout by itself.' in TMUX_AGENT_SOURCE
