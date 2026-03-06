#!/usr/bin/env python3
"""Unit tests for _lib.py shared safety library."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add hooks dir to path for direct import
HOOKS_DIR = Path(__file__).parent.parent.parent / "scripts" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from _lib import (
    _deep_merge,
    _most_restrictive,
    allow,
    ask,
    deny,
    fail_close,
    get_category_decision,
    is_in_prefixes,
    resolve_path,
)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str | None = None
    def mark_pass(self) -> None:
        self.passed = True
    def mark_fail(self, error: str) -> None:
        self.passed = False
        self.error = error
    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"  {status}: {self.name}"
        if self.error:
            msg += f"\n    Error: {self.error}"
        return msg


def test_most_restrictive() -> TestResult:
    r = TestResult("most_restrictive: deny > ask > allow")
    try:
        assert _most_restrictive("deny", "allow") == "deny"
        assert _most_restrictive("allow", "deny") == "deny"
        assert _most_restrictive("ask", "allow") == "ask"
        assert _most_restrictive("allow", "ask") == "ask"
        assert _most_restrictive("deny", "ask") == "deny"
        assert _most_restrictive("allow", "allow") == "allow"
        assert _most_restrictive("deny", "deny") == "deny"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_deep_merge_basic() -> TestResult:
    r = TestResult("deep_merge: basic dict merge")
    try:
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        overlay = {"b": {"c": 99, "e": 4}, "f": 5}
        result = _deep_merge(base, overlay)
        assert result["a"] == 1
        assert result["b"]["c"] == 99
        assert result["b"]["d"] == 3
        assert result["b"]["e"] == 4
        assert result["f"] == 5
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_deep_merge_categories_most_restrictive() -> TestResult:
    r = TestResult("deep_merge: categories use most-restrictive-wins")
    try:
        base = {"categories": {"git-destructive": "deny", "file-destruction": "allow"}}
        overlay = {"categories": {"git-destructive": "allow", "file-destruction": "deny"}}
        result = _deep_merge(base, overlay)
        # Most restrictive wins: deny beats allow
        assert result["categories"]["git-destructive"] == "deny"
        assert result["categories"]["file-destruction"] == "deny"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_deep_merge_list_replacement() -> TestResult:
    r = TestResult("deep_merge: lists are replaced not merged")
    try:
        base = {"allowed": ["/a/", "/b/"]}
        overlay = {"allowed": ["/c/"]}
        result = _deep_merge(base, overlay)
        assert result["allowed"] == ["/c/"]
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_get_category_decision_defaults() -> TestResult:
    r = TestResult("get_category_decision: returns ask by default")
    try:
        config: dict = {}
        assert get_category_decision(config, "destructive_bash", "git-destructive") == "ask"

        config = {"destructive_bash": {"categories": {"git-destructive": "deny"}}}
        assert get_category_decision(config, "destructive_bash", "git-destructive") == "deny"
        assert get_category_decision(config, "destructive_bash", "unknown-cat") == "ask"
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_resolve_path() -> TestResult:
    r = TestResult("resolve_path: expands ~ and resolves symlinks")
    try:
        home = os.path.expanduser("~")
        result = resolve_path("~/test/file.txt")
        assert result.startswith(home)
        assert "~" not in result
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_is_in_prefixes() -> TestResult:
    r = TestResult("is_in_prefixes: matches resolved prefixes")
    try:
        assert is_in_prefixes("/tmp/foo/bar.txt", ["/tmp/foo/"])
        assert not is_in_prefixes("/var/log/test.txt", ["/tmp/foo/"])
        assert is_in_prefixes("~/projects/test/a.py", ["~/projects/"])
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_fail_close_decorator() -> TestResult:
    r = TestResult("fail_close: catches exceptions and denies")
    try:
        import io
        from contextlib import redirect_stdout

        @fail_close
        def bad_main() -> None:
            raise ValueError("test error")

        buf = io.StringIO()
        with redirect_stdout(buf):
            bad_main()

        output = json.loads(buf.getvalue().strip())
        decision = output["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny", f"Expected deny on error, got {decision}"
        assert "test error" in output["hookSpecificOutput"]["permissionDecisionReason"]
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_decision_helpers_output() -> TestResult:
    r = TestResult("deny/allow/ask: produce correct JSON output")
    try:
        import io
        from contextlib import redirect_stdout

        # Test deny
        buf = io.StringIO()
        with redirect_stdout(buf):
            deny("test reason")
        out = json.loads(buf.getvalue())
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "test reason"

        # Test allow
        buf = io.StringIO()
        with redirect_stdout(buf):
            allow()
        out = json.loads(buf.getvalue())
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

        # Test ask
        buf = io.StringIO()
        with redirect_stdout(buf):
            ask("confirm?")
        out = json.loads(buf.getvalue())
        assert out["hookSpecificOutput"]["permissionDecision"] == "ask"
        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "confirm?"

        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running _lib.py unit tests...\n")
    tests = [
        test_most_restrictive, test_deep_merge_basic,
        test_deep_merge_categories_most_restrictive,
        test_deep_merge_list_replacement, test_get_category_decision_defaults,
        test_resolve_path, test_is_in_prefixes,
        test_fail_close_decorator, test_decision_helpers_output,
    ]
    passed = failed = 0
    for t in tests:
        result = t()
        print(result)
        if result.passed:
            passed += 1
        else:
            failed += 1
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} total")
    if failed:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
