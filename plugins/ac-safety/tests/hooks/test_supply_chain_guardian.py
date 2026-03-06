#!/usr/bin/env python3
"""Unit tests for supply-chain-guardian hook."""

import json
import subprocess
from pathlib import Path


HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "supply-chain-guardian.py"


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


def test_allows_npm_install() -> TestResult:
    r = TestResult("Allows npm install (lockfile)")
    try:
        out = run_hook("npm install")
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_allows_uv_sync() -> TestResult:
    r = TestResult("Allows uv sync")
    try:
        out = run_hook("uv sync")
        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_asks_pip_install_direct() -> TestResult:
    r = TestResult("Asks for pip install direct package (default: ask)")
    try:
        out = run_hook("pip install requests")
        # Default category decision is ask
        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_asks_npx_unknown_package() -> TestResult:
    r = TestResult("Asks for npx with unknown package (default: ask)")
    try:
        out = run_hook("npx malicious-package")
        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running supply-chain-guardian unit tests...\n")
    tests = [test_allows_npm_install, test_allows_uv_sync,
             test_asks_pip_install_direct, test_asks_npx_unknown_package]
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
