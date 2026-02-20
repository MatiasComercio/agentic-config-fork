#!/usr/bin/env python3
"""Unit tests for plugin hook scripts and hooks.json configuration."""

import json
import subprocess
import sys
from pathlib import Path

# Resolve project root (2 levels up from tests/hooks/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_JSON = PROJECT_ROOT / "hooks" / "hooks.json"
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "hooks"


def test_hooks_json_valid():
    """hooks.json is valid JSON."""
    with HOOKS_JSON.open() as f:
        data = json.load(f)
    assert "hooks" in data, "Missing top-level 'hooks' key"


def test_hooks_json_structure():
    """hooks.json has correct nested structure per plugin format."""
    with HOOKS_JSON.open() as f:
        data = json.load(f)

    hooks = data["hooks"]
    assert "PreToolUse" in hooks, "Missing PreToolUse event"
    entries = hooks["PreToolUse"]
    assert isinstance(entries, list), "PreToolUse must be a list"
    assert len(entries) == 3, f"Expected 3 hook entries, got {len(entries)}"

    for entry in entries:
        assert "matcher" in entry, "Missing 'matcher' field"
        assert "hooks" in entry, "Missing 'hooks' array"
        assert isinstance(entry["hooks"], list), "'hooks' must be a list"
        for hook in entry["hooks"]:
            assert hook["type"] == "command", f"Expected type 'command', got {hook['type']}"
            assert "CLAUDE_PLUGIN_ROOT" in hook["command"], \
                f"Command missing CLAUDE_PLUGIN_ROOT: {hook['command']}"


def test_hooks_json_matchers():
    """Correct matchers for each hook."""
    with HOOKS_JSON.open() as f:
        data = json.load(f)

    entries = data["hooks"]["PreToolUse"]
    matchers = [e["matcher"] for e in entries]
    assert matchers[0] == "Write|Edit|NotebookEdit|Bash", \
        f"dry-run-guard matcher wrong: {matchers[0]}"
    assert matchers[1] == "Bash", f"git-commit-guard matcher wrong: {matchers[1]}"
    assert matchers[2] == "Bash", f"gsuite-guard matcher wrong: {matchers[2]}"


def test_hooks_json_no_bash_wrapper():
    """No bash -c wrappers or .agentic-config.json references."""
    text = HOOKS_JSON.read_text()
    assert "bash -c" not in text, "Found bash -c wrapper in hooks.json"
    assert ".agentic-config.json" not in text, "Found .agentic-config.json in hooks.json"


def test_hooks_json_no_mux_hooks():
    """MUX hooks must NOT be in hooks.json (they stay in skill frontmatter)."""
    text = HOOKS_JSON.read_text()
    assert "mux" not in text.lower(), "Found mux reference in hooks.json"


def test_scripts_exist():
    """All 3 hook scripts exist in scripts/hooks/."""
    expected = ["dry-run-guard.py", "git-commit-guard.py", "gsuite-public-asset-guard.py"]
    for name in expected:
        path = SCRIPTS_DIR / name
        assert path.exists(), f"Missing script: {path}"


def test_scripts_executable():
    """All hook scripts are executable."""
    import os
    for py_file in SCRIPTS_DIR.glob("*.py"):
        assert os.access(py_file, os.X_OK), f"Not executable: {py_file.name}"


def test_scripts_have_shebang():
    """All hook scripts have uv run shebang."""
    for py_file in SCRIPTS_DIR.glob("*.py"):
        first_line = py_file.read_text().split("\n")[0]
        assert "uv run" in first_line, f"Missing uv shebang: {py_file.name}"


def test_dry_run_guard_no_hardcoded_paths():
    """dry-run-guard.py has no hardcoded path resolution."""
    text = (SCRIPTS_DIR / "dry-run-guard.py").read_text()
    assert "find_agentic_root" not in text, "Still has find_agentic_root()"
    assert ".agentic-config.json" not in text, "Still references .agentic-config.json"
    assert "sys.argv[1]" not in text, "Still parses CLI arg for project root"
    # Ensure it uses CWD for project root
    assert "Path.cwd()" in text, "Must use Path.cwd() for project root"


def _run_hook(script_name: str, stdin_data: dict) -> dict:
    """Run a hook script with given stdin and return parsed JSON output."""
    script_path = SCRIPTS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Parse first line of stdout as JSON (hooks print JSON to stdout)
    output_line = result.stdout.strip().split("\n")[0]
    return json.loads(output_line)


def test_git_commit_guard_blocks_no_verify():
    """git-commit-guard blocks git commit --no-verify."""
    stdin = {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'test' --no-verify"}
    }
    output = _run_hook("git-commit-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny", f"Expected deny, got {decision}"


def test_git_commit_guard_allows_clean_commit():
    """git-commit-guard allows normal git commit."""
    stdin = {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'clean commit'"}
    }
    output = _run_hook("git-commit-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "allow", f"Expected allow, got {decision}"


def test_git_commit_guard_allows_non_bash():
    """git-commit-guard allows non-Bash tools."""
    stdin = {
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt"}
    }
    output = _run_hook("git-commit-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "allow", f"Expected allow, got {decision}"


def test_gsuite_guard_blocks_public():
    """gsuite-public-asset-guard blocks type="anyone"."""
    stdin = {
        "tool_name": "Bash",
        "tool_input": {"command": 'gsuite share --extra \'{"type": "anyone"}\''}
    }
    output = _run_hook("gsuite-public-asset-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny", f"Expected deny, got {decision}"


def test_gsuite_guard_allows_normal():
    """gsuite-public-asset-guard allows normal commands."""
    stdin = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"}
    }
    output = _run_hook("gsuite-public-asset-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "allow", f"Expected allow, got {decision}"


def test_dry_run_guard_allows_when_no_status():
    """dry-run-guard allows when no status.yml exists (fail-open)."""
    stdin = {
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt"}
    }
    output = _run_hook("dry-run-guard.py", stdin)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "allow", f"Expected allow (no status file), got {decision}"


if __name__ == "__main__":
    # Simple test runner
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test_fn.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed else 0)
