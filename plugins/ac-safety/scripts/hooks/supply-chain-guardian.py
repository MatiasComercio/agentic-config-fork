#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
PreToolUse hook: blocks unapproved package installations.

Config-driven via safety.yaml (supply_chain section).
Default category decisions: ASK. Fail-close on errors.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import allow, ask, deny, fail_close, get_category_decision, load_config

# Patterns that are SAFE (skip blocking)
SAFE_PATTERNS = [
    re.compile(r"\bnpm\s+(install|ci)\s*$"),
    re.compile(r"\bnpm\s+(install|ci)\s+--"),
    re.compile(r"\bpip\s+install\s+(-r\s|--requirement\s|-e\s|--editable\s|\.\s*$)"),
    re.compile(r"\buv\s+sync\b"),
    re.compile(r"\buv\s+run\b"),
    re.compile(r"\buv\s+pip\s+install\s+(-r\s|--requirement\s|-e\s|--editable\s|\.\s*$)"),
    re.compile(r"\buv\s+pip\s+compile\b"),
]


def _apply_decision(config: dict, category: str, reason: str) -> None:
    """Apply the configured decision for a supply_chain category."""
    decision = get_category_decision(config, "supply_chain", category)
    if decision == "deny":
        deny(f"BLOCKED: {reason}. Supply-chain-guardian.")
    elif decision == "ask":
        ask(f"{reason} -- confirm to proceed?")
    else:
        allow()


def _is_npx_blocked(command: str, npx_allowlist: set[str]) -> str | None:
    match = re.search(r"\bnpx\s+(?:--yes\s+)?(@?[\w/-]+(?:@[\w./-]+)?)", command)
    if not match:
        return None
    package = match.group(1)
    base_package = re.sub(r"@[\w./-]+$", "", package) if not package.startswith("@") else \
                   re.sub(r"@[\w./-]+$", "", package) if package.count("@") > 1 else package
    if base_package in npx_allowlist:
        return None
    return f"npx with unapproved package '{package}' (not in allowlist)"


def _is_pip_blocked(command: str) -> str | None:
    if not re.search(r"\bpip\s+install\b", command):
        return None
    for safe in SAFE_PATTERNS:
        if safe.search(command):
            return None
    return "pip install of direct package (use requirements.txt instead)"


def _is_uv_add_blocked(command: str, uv_add_allowlist: set[str]) -> str | None:
    match = re.search(r"\buv\s+add\s+(\S+)", command)
    if not match:
        return None
    package = match.group(1)
    if package.startswith("-"):
        return None
    if package in uv_add_allowlist:
        return None
    return f"uv add with unapproved package '{package}' (not in allowlist)"


def _is_uv_pip_blocked(command: str) -> str | None:
    if not re.search(r"\buv\s+pip\s+install\b", command):
        return None
    for safe in SAFE_PATTERNS:
        if safe.search(command):
            return None
    return "uv pip install of direct package (use requirements.txt or uv sync)"


@fail_close
def main() -> None:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        allow()
        return

    command = tool_input.get("command", "")

    # Fast path: safe patterns always allowed
    for safe in SAFE_PATTERNS:
        if safe.search(command):
            allow()
            return

    config = load_config()
    sc = config.get("supply_chain", {})
    if not isinstance(sc, dict):
        sc = {}

    npx_allowlist = set(sc.get("npx_allowlist", [
        "@playwright/mcp", "ts-node", "cdk", "aws-cdk", "jest", "tsx", "tsc", "prettier", "eslint",
    ]))
    uv_add_allowlist = set(sc.get("uv_add_allowlist", []))

    # Check each supply chain risk
    checks: list[tuple[str | None, str]] = [
        (_is_npx_blocked(command, npx_allowlist), "npx-packages"),
        (_is_pip_blocked(command), "pip-direct"),
        (_is_uv_add_blocked(command, uv_add_allowlist), "uv-add"),
        (_is_uv_pip_blocked(command), "uv-pip-direct"),
    ]
    for reason, category in checks:
        if reason:
            _apply_decision(config, category, reason)
            return

    allow()


if __name__ == "__main__":
    main()
