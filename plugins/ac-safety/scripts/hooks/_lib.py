"""
Shared library for ac-safety guardian hooks.

Provides config loading (3-tier deep-merge), decision helpers,
path utilities, and fail-close error handling.
"""

import json
import os
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import yaml

# Decision priority for most-restrictive-wins resolution
_DECISION_PRIORITY: dict[str, int] = {"deny": 0, "ask": 1, "allow": 2}


def _most_restrictive(a: str, b: str) -> str:
    """Return the more restrictive of two decisions (deny > ask > allow)."""
    pa = _DECISION_PRIORITY.get(a, 1)  # unknown defaults to ask
    pb = _DECISION_PRIORITY.get(b, 1)
    return a if pa <= pb else b


def _deep_merge(base: dict, overlay: dict) -> dict:
    """
    Deep-merge overlay into base. Returns new dict.

    For category decision dicts, applies most-restrictive-wins.
    For lists, overlay replaces base entirely.
    For dicts, recursively merge.
    """
    result = dict(base)
    for key, overlay_val in overlay.items():
        if key not in result:
            result[key] = overlay_val
        elif isinstance(result[key], dict) and isinstance(overlay_val, dict):
            # Check if this is a "categories" dict (values are decision strings)
            if key == "categories":
                merged_cats: dict[str, str] = dict(result[key])
                for cat_key, cat_val in overlay_val.items():
                    if cat_key in merged_cats:
                        merged_cats[cat_key] = _most_restrictive(merged_cats[cat_key], str(cat_val))
                    else:
                        merged_cats[cat_key] = str(cat_val)
                result[key] = merged_cats
            else:
                result[key] = _deep_merge(result[key], overlay_val)
        else:
            # Lists and scalars: overlay replaces
            result[key] = overlay_val
    return result


def _find_plugin_root() -> Path:
    """Find plugin root from CLAUDE_PLUGIN_ROOT env or relative to this file."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    # Fallback: scripts/hooks/_lib.py -> plugin root is ../..
    return Path(__file__).resolve().parent.parent.parent


def load_config(guardian_name: str | None = None) -> dict[str, Any]:
    """
    Load safety config with 3-tier deep-merge resolution.

    Priority (most-restrictive-wins at category level):
      1. Project-level: $CWD/safety.yaml or $CLAUDE_PROJECT_DIR/safety.yaml
      2. User-level: ~/.claude/safety.yaml
      3. Plugin defaults: <plugin_root>/config/safety.default.yaml

    Args:
        guardian_name: If provided, return only that guardian's section merged
                       with top-level keys (allowed_project_roots, etc.)

    Returns:
        Merged config dict.
    """
    plugin_root = _find_plugin_root()

    # Layer 1: Plugin defaults (base)
    defaults_path = plugin_root / "config" / "safety.default.yaml"
    config: dict[str, Any] = {}
    if defaults_path.is_file():
        with open(defaults_path) as f:
            config = yaml.safe_load(f) or {}

    # Layer 2: User-level
    user_path = Path.home() / ".claude" / "safety.yaml"
    if user_path.is_file():
        with open(user_path) as f:
            user_cfg = yaml.safe_load(f) or {}
        config = _deep_merge(config, user_cfg)

    # Layer 3: Project-level
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    project_path = Path(project_dir) / "safety.yaml"
    if project_path.is_file():
        with open(project_path) as f:
            proj_cfg = yaml.safe_load(f) or {}
        config = _deep_merge(config, proj_cfg)

    return config


def get_category_decision(config: dict[str, Any], guardian: str, category: str) -> str:
    """
    Get the resolved decision for a guardian category.

    Returns "deny", "ask", or "allow". Defaults to "ask" if not configured.
    """
    guardian_cfg = config.get(guardian, {})
    if not isinstance(guardian_cfg, dict):
        return "ask"
    categories = guardian_cfg.get("categories", {})
    if not isinstance(categories, dict):
        return "ask"
    decision = str(categories.get(category, "ask")).lower()
    if decision not in _DECISION_PRIORITY:
        return "ask"
    return decision


def resolve_path(path: str) -> str:
    """Resolve path: expanduser + realpath."""
    return os.path.realpath(os.path.expanduser(path))


def is_in_prefixes(path: str, prefixes: list[str]) -> bool:
    """Check if resolved path starts with any resolved prefix."""
    resolved = resolve_path(path)
    for prefix in prefixes:
        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
        if resolved.startswith(real_prefix + "/") or resolved == real_prefix:
            return True
    return False


def deny(reason: str) -> None:
    """Print JSON deny decision to stdout."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def allow() -> None:
    """Print JSON allow decision to stdout."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }))


def ask(reason: str) -> None:
    """Print JSON ask decision to stdout."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def fail_close(func: Callable[[], None]) -> Callable[[], None]:
    """
    Decorator: wraps hook main() with fail-close error handling.
    On ANY exception (config parse, unexpected error), deny the operation.
    """
    @wraps(func)
    def wrapper() -> None:
        try:
            func()
        except Exception as e:
            deny(f"Hook error (fail-close): {e}")
            print(f"Hook error (fail-close): {e}", file=sys.stderr)
    return wrapper
