#!/usr/bin/env python3
"""Unit tests for write-scope-guardian hook."""

import json
import os
import subprocess
from pathlib import Path


HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "write-scope-guardian.py"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str | None = None
    def mark_pass(self) -> None:
        self.passed = True
    def mark_fail(self, error: str) -> None:
        self.error = error
    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"  {status}: {self.name}"
        if self.error:
            msg += f"\n    Error: {self.error}"
        return msg


def run_hook(tool_name: str, tool_input: dict) -> dict:
    result = subprocess.run(
        [str(HOOK_PATH)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True,
    )
    output = json.loads(result.stdout)
    hook_out = output.get("hookSpecificOutput", {})
    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}


def test_allows_project_write() -> TestResult:
    r = TestResult("Allows Write to ~/projects/")
    try:
        out = run_hook("Write", {"file_path": os.path.expanduser("~/projects/test/file.py"), "content": "test"})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_settings_write() -> TestResult:
    r = TestResult("Blocks Write to ~/.claude/settings.json")
    try:
        out = run_hook("Write", {"file_path": os.path.expanduser("~/.claude/settings.json"), "content": "{}"})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_asks_hooks_write() -> TestResult:
    r = TestResult("Asks for Write to ~/.claude/hooks/")
    try:
        out = run_hook("Write", {"file_path": os.path.expanduser("~/.claude/hooks/test.py"), "content": "test"})
        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_system_write() -> TestResult:
    r = TestResult("Blocks Write to /etc/")
    try:
        out = run_hook("Write", {"file_path": "/etc/passwd", "content": "test"})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_git_hooks_injection() -> TestResult:
    r = TestResult("Blocks Write to .git/hooks/")
    try:
        out = run_hook("Write", {"file_path": "/tmp/repo/.git/hooks/pre-commit", "content": "test"})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running write-scope-guardian unit tests...\n")
    tests = [test_allows_project_write, test_blocks_settings_write,
             test_asks_hooks_write, test_blocks_system_write, test_blocks_git_hooks_injection]
    passed = failed = 0
    for t in tests:
        result = t()
        print(result)
        passed += 1 if result.passed else 0
        failed += 0 if result.passed else 1
    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
    if failed:
        exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
