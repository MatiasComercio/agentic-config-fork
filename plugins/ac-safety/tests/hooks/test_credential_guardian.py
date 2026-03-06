#!/usr/bin/env python3
"""Unit tests for credential-guardian hook."""

import json
import os
import subprocess
from pathlib import Path


HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "credential-guardian.py"


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


def test_blocks_ssh_read() -> TestResult:
    r = TestResult("Blocks Read of ~/.ssh/")
    try:
        out = run_hook("Read", {"file_path": os.path.expanduser("~/.ssh/id_rsa")})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_aws_grep() -> TestResult:
    r = TestResult("Blocks Grep in ~/.aws/")
    try:
        out = run_hook("Grep", {"path": os.path.expanduser("~/.aws/credentials"), "pattern": "secret"})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_project_read() -> TestResult:
    r = TestResult("Allows Read in ~/projects/")
    try:
        out = run_hook("Read", {"file_path": os.path.expanduser("~/projects/test/file.py")})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_claude_settings() -> TestResult:
    r = TestResult("Allows Read of ~/.claude/settings.json")
    try:
        out = run_hook("Read", {"file_path": os.path.expanduser("~/.claude/settings.json")})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_non_read_tools() -> TestResult:
    r = TestResult("Allows non-Read tools (Bash)")
    try:
        out = run_hook("Bash", {"command": "ls"})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_fail_close_on_bad_input() -> TestResult:
    r = TestResult("Fail-close on invalid JSON input")
    try:
        result = subprocess.run(
            [str(HOOK_PATH)], input="not valid json",
            capture_output=True, text=True,
        )
        output = json.loads(result.stdout)
        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
        assert decision == "deny", f"Expected deny on error, got {decision}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running credential-guardian unit tests...\n")
    tests = [test_blocks_ssh_read, test_blocks_aws_grep, test_allows_project_read,
             test_allows_claude_settings, test_allows_non_read_tools, test_fail_close_on_bad_input]
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
