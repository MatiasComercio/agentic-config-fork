#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Claude Code Tool Audit Hook.

Displays real-time tool usage via systemMessage and writes
append-only JSONL audit log. Config-driven via audit.default.yaml.
Fail-close on errors.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", str(os.getpid()))


def _find_plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parent.parent.parent


def _load_audit_config() -> dict:
    plugin_root = _find_plugin_root()
    defaults_path = plugin_root / "config" / "audit.default.yaml"
    config: dict = {}
    if defaults_path.is_file():
        with open(defaults_path) as f:
            config = yaml.safe_load(f) or {}

    # User override
    user_path = Path.home() / ".claude" / "audit.yaml"
    if user_path.is_file():
        with open(user_path) as f:
            user_cfg = yaml.safe_load(f) or {}
        config.update(user_cfg)

    # Project override
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    project_path = Path(project_dir) / "audit.yaml"
    if project_path.is_file():
        with open(project_path) as f:
            proj_cfg = yaml.safe_load(f) or {}
        config.update(proj_cfg)

    return config


def _truncate_field_values(obj: object, max_words: int = 50) -> object:
    if isinstance(obj, dict):
        return {k: _truncate_field_values(v, max_words) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_truncate_field_values(item, max_words) for item in obj]
    elif isinstance(obj, str):
        words = obj.split()
        if len(words) > max_words:
            return " ".join(words[:max_words]) + "..."
        return obj
    return obj


def _format_simple(data: dict, indent: int = 0) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{'  ' * indent}{key}:")
            lines.append(_format_simple(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{'  ' * indent}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_format_simple(item, indent + 1))
                else:
                    lines.append(f"{'  ' * (indent + 1)}- {item}")
        else:
            lines.append(f"{'  ' * indent}{key}: {value}")
    return "\n".join(lines)


def _write_audit_log(tool_name: str, tool_input: dict, log_dir: str, log_permissions: int) -> None:
    log_path = Path(log_dir)
    if not log_path.exists():
        return  # Silently skip if dir missing
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"{today}.jsonl"
    entry = {"ts": datetime.now().isoformat(), "tool": tool_name, "input": tool_input, "session": SESSION_ID}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    try:
        log_file.chmod(log_permissions)
    except OSError:
        pass


def main() -> None:
    try:
        json_input = sys.stdin.read().strip()
        if not json_input:
            print(json.dumps({"systemMessage": "[AUDIT] No input received"}))
            return

        data = json.loads(json_input)
        tool_name = data.get("tool_name", "Unknown")
        tool_input = data.get("tool_input", {})

        config = _load_audit_config()
        log_dir = config.get("log_dir", "/var/log/claude-audit")
        log_permissions = config.get("log_permissions", 0o600)
        display_tools = set(config.get("display_tools", ["Bash"]))
        max_words = config.get("max_words", 50)

        _write_audit_log(tool_name, tool_input, log_dir, log_permissions)

        if tool_name in display_tools:
            truncated = _truncate_field_values(tool_input, max_words)
            message = f"{tool_name}:\n{_format_simple(truncated) if isinstance(truncated, dict) else str(truncated)}"
            print(json.dumps({"systemMessage": message}))

    except Exception as e:
        # Fail-close: deny on audit errors
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Audit hook error (fail-close): {e}",
            }
        }))
        print(f"Audit hook error (fail-close): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
