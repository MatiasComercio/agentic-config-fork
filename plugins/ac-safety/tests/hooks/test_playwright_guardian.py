#!/usr/bin/env python3
"""Unit tests for playwright-guardian hook."""

import json
import subprocess
from pathlib import Path


HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "playwright-guardian.py"


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


def test_blocks_browser_evaluate() -> TestResult:
    r = TestResult("Blocks browser_evaluate (always blocked)")
    try:
        out = run_hook("mcp__playwright__browser_evaluate", {"script": "document.cookie"})
        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_browser_snapshot() -> TestResult:
    r = TestResult("Allows browser_snapshot (always allowed)")
    try:
        out = run_hook("mcp__playwright__browser_snapshot", {})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_navigate_allowed_domain() -> TestResult:
    r = TestResult("Allows navigate to github.com")
    try:
        out = run_hook("mcp__playwright__browser_navigate", {"url": "https://github.com/test"})
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_asks_navigate_blocked_domain() -> TestResult:
    r = TestResult("Asks for navigate to unknown domain (default: ask)")
    try:
        out = run_hook("mcp__playwright__browser_navigate", {"url": "https://evil.com/phishing"})
        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running playwright-guardian unit tests...\n")
    tests = [test_blocks_browser_evaluate, test_allows_browser_snapshot,
             test_allows_navigate_allowed_domain, test_asks_navigate_blocked_domain]
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
