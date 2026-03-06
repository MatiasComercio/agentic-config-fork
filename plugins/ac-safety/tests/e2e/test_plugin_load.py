#!/usr/bin/env python3
"""E2E tests: validate ac-safety and ac-audit plugin structure and loadability."""

import ast
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent.parent


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


def test_ac_safety_structure() -> TestResult:
    r = TestResult("ac-safety: all required files exist")
    try:
        base = REPO_ROOT / "ac-safety"
        required = [
            ".claude-plugin/plugin.json", "hooks/hooks.json", "config/safety.default.yaml",
            "scripts/hooks/_lib.py", "scripts/hooks/credential-guardian.py",
            "scripts/hooks/destructive-bash-guardian.py", "scripts/hooks/write-scope-guardian.py",
            "scripts/hooks/supply-chain-guardian.py", "scripts/hooks/playwright-guardian.py",
            "skills/configure-safety/SKILL.md", "CLAUDE.md", "README.md",
        ]
        for f in required:
            assert (base / f).exists(), f"Missing: {f}"
        # Validate JSON files
        json.loads((base / ".claude-plugin/plugin.json").read_text())
        json.loads((base / "hooks/hooks.json").read_text())
        # Validate YAML
        yaml.safe_load((base / "config/safety.default.yaml").read_text())
        # Validate Python syntax
        for py in base.glob("scripts/hooks/*.py"):
            ast.parse(py.read_text())
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def test_ac_audit_structure() -> TestResult:
    r = TestResult("ac-audit: all required files exist")
    try:
        base = REPO_ROOT / "ac-audit"
        required = [
            ".claude-plugin/plugin.json", "hooks/hooks.json", "config/audit.default.yaml",
            "scripts/hooks/tool-audit.py", "CLAUDE.md", "README.md",
        ]
        for f in required:
            assert (base / f).exists(), f"Missing: {f}"
        json.loads((base / ".claude-plugin/plugin.json").read_text())
        json.loads((base / "hooks/hooks.json").read_text())
        yaml.safe_load((base / "config/audit.default.yaml").read_text())
        ast.parse((base / "scripts/hooks/tool-audit.py").read_text())
        r.mark_pass()
    except Exception as e:
        r.mark_fail(str(e))
    return r


def main() -> None:
    print("Running E2E plugin structure tests...\n")
    tests = [test_ac_safety_structure, test_ac_audit_structure]
    passed = failed = 0
    for t in tests:
        result = t()
        print(result)
        passed += 1 if result.passed else 0
        failed += 0 if result.passed else 1
    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
    if failed:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
