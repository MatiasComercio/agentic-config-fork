#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Pretooluse hook that blocks forbidden tools during MUX skill execution.

Session-scoped via mux-active marker file.
Fail-closed: deny operations if hook encounters errors (MUX must enforce compliance).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

FORBIDDEN_TOOLS = {
    "Read", "Write", "Edit", "Grep", "Glob",
    "WebSearch", "WebFetch", "Skill", "NotebookEdit"
}


def find_agentic_root() -> Path:
    """Find agentic-config installation root."""
    current = Path.cwd()
    for _ in range(10):
        if (current / "VERSION").exists() and (current / "core").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd()


def find_claude_pid() -> int | None:
    """Trace up process tree to find claude process PID."""
    try:
        pid = os.getpid()
        for _ in range(10):
            result = subprocess.run(
                ["ps", "-o", "pid=,ppid=,comm=", "-p", str(pid)],
                capture_output=True, text=True
            )
            line = result.stdout.strip()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 3:
                current_pid, ppid, comm = int(parts[0]), int(parts[1]), parts[2]
                if "claude" in comm.lower():
                    return current_pid
                pid = ppid
            else:
                break
    except Exception:
        pass
    return None


def is_mux_active() -> bool:
    """Check if MUX skill is active for current Claude session."""
    claude_pid = find_claude_pid()
    if not claude_pid:
        return False
    agentic_root = find_agentic_root()
    marker = agentic_root / f"outputs/session/{claude_pid}/mux-active"
    return marker.exists()


def main() -> None:
    """Main hook execution."""
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")

        # Only enforce when MUX is active
        if not is_mux_active():
            output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
            print(json.dumps(output))
            return

        # Block forbidden tools
        if tool_name in FORBIDDEN_TOOLS:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"MUX VIOLATION: {tool_name} is forbidden. Delegate via Task()."
                }
            }
        else:
            output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}

        print(json.dumps(output))

    except Exception as e:
        # Fail-closed: block on error to enforce MUX compliance
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"MUX hook error (fail-closed): {e}"
            }
        }
        print(json.dumps(output))
        sys.exit(0)


if __name__ == "__main__":
    main()
