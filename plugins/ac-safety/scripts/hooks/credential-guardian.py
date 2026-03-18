#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
PreToolUse hook: blocks Read/Grep/Glob access to credential files.

Config-driven via safety.yaml (credential_guardian section).
Default decision: DENY. Fail-close on errors.
"""

import json
import os
import re
import sys

# Import shared library via sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import allow, ask, deny, fail_close, get_category_decision, is_in_prefixes, load_config, resolve_path

READ_TOOLS = {"Read", "Grep", "Glob"}


def _extract_paths(tool_name: str, tool_input: dict) -> list[str]:
    """Extract file paths from tool input based on tool type."""
    paths: list[str] = []
    if tool_name == "Read":
        p = tool_input.get("file_path", "")
        if p:
            paths.append(p)
    elif tool_name == "Grep":
        p = tool_input.get("path", "")
        if p:
            paths.append(p)
        g = tool_input.get("glob", "")
        if g and "/" in g:
            paths.append(g)
    elif tool_name == "Glob":
        p = tool_input.get("path", "")
        if p:
            paths.append(p)
        pat = tool_input.get("pattern", "")
        if pat and (pat.startswith("/") or pat.startswith("~/")):
            paths.append(pat)
    return paths


def _categorize_block(prefix: str) -> str:
    """Map a blocked prefix to its credential category."""
    p = prefix.rstrip("/").lower()
    if ".ssh" in p:
        return "ssh-keys"
    if ".aws" in p or ".docker" in p or ".config/gh" in p:
        return "cloud-credentials"
    if ".gnupg" in p:
        return "cloud-credentials"
    if "library" in p:
        return "browser-credentials"
    if ".claude" in p:
        return "app-tokens"
    return "cloud-credentials"


def _is_blocked(
    path: str,
    blocked_prefixes: list[str],
    blocked_filenames: list[str],
    blocked_extensions: list[str],
    allowed_project_roots: list[str],
    allowed_claude_files: list[str],
) -> tuple[str | None, str]:
    """Returns (block_reason, category) or (None, '') if allowed."""
    resolved = resolve_path(path)

    # Always-blocked absolute prefixes (use is_in_prefixes logic for consistency)
    for prefix in blocked_prefixes:
        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
        if resolved.startswith(real_prefix + "/") or resolved == real_prefix:
            # Exception for explicitly allowed claude files
            if any(resolved == os.path.realpath(os.path.expanduser(f)) for f in allowed_claude_files):
                return None, ""
            category = _categorize_block(prefix)
            return f"Access to {prefix} is blocked (credential protection)", category

    # Blocked filenames in home dir
    basename = os.path.basename(resolved)
    home = os.path.expanduser("~")
    if basename in blocked_filenames and resolved.startswith(home + "/"):
        return f"Access to {basename} is blocked (credential file)", "app-tokens"

    # Outside project roots: block sensitive extensions and .env
    if not is_in_prefixes(path, allowed_project_roots + ["/private/tmp/", "/tmp/"]):
        _, ext = os.path.splitext(resolved)
        if ext.lower() in blocked_extensions:
            return f"Access to {ext} files outside project dirs is blocked", "ssh-keys"
        if re.search(r"(^|/)\.env(\..+)?$", os.path.basename(resolved)):
            return "Access to .env files outside project dirs is blocked", "env-files"

    return None, ""


@fail_close
def main() -> None:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in READ_TOOLS:
        allow()
        return

    config = load_config()
    cg = config.get("credential_guardian", {})
    if not isinstance(cg, dict):
        cg = {}

    blocked_prefixes: list[str] = cg.get("blocked_prefixes", [
        "~/.aws/", "~/.ssh/", "~/.config/gh/", "~/.docker/",
        "~/.gnupg/", "~/Library/", "~/.claude/debug/", "~/.claude/.claude.json",
    ])
    blocked_filenames: list[str] = cg.get("blocked_filenames", [
        ".npmrc", ".netrc", ".pypirc", ".git-credentials",
    ])
    blocked_extensions: list[str] = cg.get("blocked_extensions", [".pem", ".key", ".p12", ".pfx"])
    allowed_project_roots: list[str] = config.get("allowed_project_roots", ["~/projects/"])
    allowed_claude_files: list[str] = cg.get("allowed_claude_files", [
        "~/.claude/settings.json", "~/.claude/settings.local.json", "~/.claude/CLAUDE.md",
    ])

    paths = _extract_paths(tool_name, tool_input)
    for path in paths:
        reason, category = _is_blocked(path, blocked_prefixes, blocked_filenames, blocked_extensions, allowed_project_roots, allowed_claude_files)
        if reason:
            # Default to deny if category not found (fail-close)
            decision = get_category_decision(config, "credential_guardian", category) if category else "deny"
            if decision == "deny":
                deny(f"BLOCKED: {reason}")
            elif decision == "ask":
                ask(f"{reason} -- confirm to proceed?")
            else:
                allow()
            return

    allow()


if __name__ == "__main__":
    main()
