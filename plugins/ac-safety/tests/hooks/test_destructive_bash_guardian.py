#!/usr/bin/env python3
"""Unit tests for destructive-bash-guardian hook."""

import json
import subprocess
from pathlib import Path


HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "destructive-bash-guardian.py"


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


def run_hook(command: str) -> dict:
    result = subprocess.run(
        [str(HOOK_PATH)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True,
    )
    output = json.loads(result.stdout)
    hook_out = output.get("hookSpecificOutput", {})
    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}


def test_blocks_rm_rf_home() -> TestResult:
    r = TestResult("Blocks rm -rf ~/")
    try:
        out = run_hook("rm -rf ~/important_stuff")
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_git_force_push() -> TestResult:
    r = TestResult("Blocks git push --force")
    try:
        out = run_hook("git push origin main --force")
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_blocks_terraform_destroy() -> TestResult:
    r = TestResult("Blocks terraform destroy")
    try:
        out = run_hook("terraform destroy -auto-approve")
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_safe_commands() -> TestResult:
    r = TestResult("Allows safe commands (ls, git status)")
    try:
        for cmd in ["ls -la", "git status", "echo hello", "cat README.md"]:
            out = run_hook(cmd)
            assert out["decision"] == "allow", f"Expected allow for '{cmd}', got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_non_bash_tools() -> TestResult:
    r = TestResult("Allows non-Bash tools")
    try:
        result = subprocess.run(
            [str(HOOK_PATH)],
            input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/test"}}),
            capture_output=True, text=True,
        )
        output = json.loads(result.stdout)
        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
        assert decision == "allow", f"Expected allow for Read, got {decision}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running destructive-bash-guardian unit tests...\n")
    tests = [test_blocks_rm_rf_home, test_blocks_git_force_push,
             test_blocks_terraform_destroy, test_allows_safe_commands,
             test_allows_non_bash_tools]
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
