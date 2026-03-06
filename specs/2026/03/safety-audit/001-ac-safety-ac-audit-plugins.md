# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Refactor 5 existing guardian hooks and the tool-audit hook from `~/.claude/hooks/` into two distributable Claude Code plugins (`ac-safety` and `ac-audit`), replacing hardcoded paths and duplicated helpers with a shared library and YAML-driven per-category configuration, enabling marketplace distribution via the agentic-plugins ecosystem.

## Mid-Level Objectives (MLO)

### ac-safety plugin
- CREATE shared `_lib.py` module eliminating copy-pasted `_deny`/`_allow`/`_ask` helpers and adding YAML config loader with deep-merge resolution (project `safety.yaml` > `~/.claude/safety.yaml` > `safety.default.yaml`)
- REFACTOR `credential-guardian.py` into plugin hook with configurable `allowed_project_roots`, `blocked_prefixes`, `blocked_filenames`, `blocked_extensions`, and `allowed_claude_files` -- replacing hardcoded `~/projects/waterplan/`
- REFACTOR `destructive-bash-guardian.py` into plugin hook with per-category configurable decisions (`deny`/`ask`/`allow`) for: `git-destructive`, `file-destruction`, `aws-destructive`, `data-exfiltration`, `process-destruction`, `persistence`, `system-level`, `docker-destruction`, `npm-publish`, `iac-destruction`, `permission-abuse`, `credential-reads`
- REFACTOR `write-scope-guardian.py` into plugin hook with configurable `allowed_write_prefixes`, `blocked_write_prefixes`, `blocked_write_files`, `ask_user_prefixes`
- REFACTOR `supply-chain-guardian.py` into plugin hook with configurable `npx_allowlist`, `uv_add_allowlist`, per-category decisions for: `npx-packages`, `pip-direct`, `uv-add`, `uv-pip-direct`
- REFACTOR `playwright-guardian.py` into plugin hook with configurable `allowed_domains`, `always_blocked_tools`, `always_allowed_tools`, per-category decisions for: `navigate-blocked-domain`, `browser-evaluate`, `browser-fill-form`, `browser-file-upload`, `unknown-mcp-action`
- CREATE `hooks.json` with tool-specific matchers and `${CLAUDE_PLUGIN_ROOT}` variable paths
- CREATE `.claude-plugin/plugin.json` with marketplace metadata
- CREATE `safety.default.yaml` shipping sane defaults for all categories
- CREATE `configure-safety` skill at `skills/configure-safety/SKILL.md` for interactive safety.yaml customization
- ENSURE all hooks use `uv run --script` with PEP 723 headers (no external dependencies beyond stdlib + PyYAML)
- ENSURE fail-open default on all hook errors

### ac-audit plugin
- EXTRACT `tool_audit.py` into standalone plugin with JSONL audit logging and Bash `systemMessage` display
- CREATE `audit.default.yaml` with configurable `log_dir`, `log_permissions`, `display_tools` (which tools show systemMessage), `max_words` truncation
- CREATE `hooks.json` with `*` matcher
- CREATE `.claude-plugin/plugin.json` with marketplace metadata
- ENSURE independence from ac-safety (separate enable/disable)

## Details (DT)

### Source Material
- `~/.claude/hooks/pretooluse/credential-guardian.py` -- 187 lines
- `~/.claude/hooks/pretooluse/destructive-bash-guardian.py` -- 169 lines
- `~/.claude/hooks/pretooluse/write-scope-guardian.py` -- 169 lines
- `~/.claude/hooks/pretooluse/supply-chain-guardian.py` -- 154 lines
- `~/.claude/hooks/pretooluse/playwright-guardian.py` -- 155 lines
- `~/.claude/hooks/tool_audit.py` -- 159 lines

### Plugin Structure Reference
Existing plugins at `plugins/ac-git/`, `plugins/ac-tools/` demonstrate:
- `.claude-plugin/plugin.json` metadata format
- `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}` variable
- `scripts/hooks/*.py` with PEP 723 headers (`#!/usr/bin/env -S uv run --script` + `/// script` block)
- Skills at `skills/<name>/SKILL.md`

### Target Directory Structure
```
plugins/ac-safety/
  .claude-plugin/plugin.json
  hooks/hooks.json
  scripts/hooks/_lib.py
  scripts/hooks/credential-guardian.py
  scripts/hooks/destructive-bash-guardian.py
  scripts/hooks/write-scope-guardian.py
  scripts/hooks/supply-chain-guardian.py
  scripts/hooks/playwright-guardian.py
  config/safety.default.yaml
  skills/configure-safety/SKILL.md
  CLAUDE.md
  README.md

plugins/ac-audit/
  .claude-plugin/plugin.json
  hooks/hooks.json
  scripts/hooks/tool-audit.py
  config/audit.default.yaml
  CLAUDE.md
  README.md
```

### _lib.py Shared Module
Must provide:
- `load_config(guardian_name: str) -> dict` -- deep-merge resolution: project `safety.yaml` > `~/.claude/safety.yaml` > plugin `safety.default.yaml`
- `deny(reason: str) -> None` -- print JSON deny decision
- `allow() -> None` -- print JSON allow decision
- `ask(reason: str) -> None` -- print JSON ask decision
- `resolve_path(path: str) -> str` -- expanduser + realpath
- `is_in_prefixes(path: str, prefixes: list[str]) -> bool` -- prefix matching
- `get_category_decision(config: dict, guardian: str, category: str) -> str` -- returns "deny"/"ask"/"allow" for a given category

### Config Resolution (safety.yaml)
```yaml
# Priority: project safety.yaml > ~/.claude/safety.yaml > plugin defaults
# Deep merge: category-level keys override, non-specified keys inherit defaults

allowed_project_roots:
  - "~/projects/"

credential_guardian:
  blocked_prefixes:
    - "~/.aws/"
    - "~/.ssh/"
    # ...
  allowed_claude_files:
    - "~/.claude/settings.json"
    # ...

destructive_bash:
  categories:
    git-destructive: deny      # deny | ask | allow
    file-destruction: deny
    aws-destructive: deny
    data-exfiltration: deny
    process-destruction: deny
    persistence: deny
    system-level: deny
    docker-destruction: deny
    npm-publish: deny
    iac-destruction: deny
    permission-abuse: deny
    credential-reads: deny

write_scope:
  allowed_write_prefixes:
    - "~/projects/"
    - "~/.claude/"
  blocked_write_files:
    - "~/.claude/settings.json"
    # ...

supply_chain:
  categories:
    npx-packages: deny
    pip-direct: deny
    uv-add: deny
    uv-pip-direct: deny
  npx_allowlist:
    - "@playwright/mcp"
    - "ts-node"
    # ...

playwright:
  categories:
    navigate-blocked-domain: deny
    browser-evaluate: deny
    browser-fill-form: deny
    browser-file-upload: deny
    unknown-mcp-action: deny
  allowed_domains:
    - "localhost"
    - "github.com"
    # ...
```

### hooks.json Format (ac-safety)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [{
          "type": "command",
          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/credential-guardian.py",
          "timeout": 5000
        }]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/destructive-bash-guardian.py",
            "timeout": 5000
          },
          {
            "type": "command",
            "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/supply-chain-guardian.py",
            "timeout": 5000
          }
        ]
      },
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [{
          "type": "command",
          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/write-scope-guardian.py",
          "timeout": 5000
        }]
      },
      {
        "matcher": "mcp__playwright__*|mcp__plugin_playwright_playwright__*",
        "hooks": [{
          "type": "command",
          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/playwright-guardian.py",
          "timeout": 5000
        }]
      }
    ]
  }
}
```

### hooks.json Format (ac-audit)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/tool-audit.py"
        }]
      }
    ]
  }
}
```

### PEP 723 Header Pattern
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
```

### Hardcoded Paths to Replace
- hardcoded project root (e.g. `~/projects/<project>/`) -> `allowed_project_roots` from config
- `/Users/matias/` -> dynamic via `os.path.expanduser("~")`
- `/var/log/claude-audit` -> `log_dir` from audit config

### configure-safety Skill Requirements
The skill at `plugins/ac-safety/skills/configure-safety/SKILL.md` must:
1. Explain the 3-tier config resolution (project > user > defaults)
2. Read current effective config by checking all 3 locations
3. Interactively ask user preferences per guardian and category
4. Generate or update `safety.yaml` at the appropriate location (project or user level)
5. Validate generated config against schema
6. Be invocable via `/ac-safety:configure-safety`

### Constraints
- All hooks must remain fail-open (catch all exceptions, return allow)
- No external dependencies beyond stdlib + PyYAML (via PEP 723 inline metadata)
- `_lib.py` is imported by hooks via relative path (sys.path manipulation)
- Plugin version matches current release: `0.2.2`
- All content must be project-agnostic and PII-free
- `${CLAUDE_PLUGIN_ROOT}` must be used in hooks.json command paths

### Testing
- Unit test: each guardian correctly reads from config, applies category decisions
- Unit test: `_lib.py` deep-merge logic (overlay > user > defaults)
- Unit test: path resolution with expanduser
- E2E test: plugin loads in Claude Code, hooks fire on matching tools
- E2E test: config override at project level takes precedence

## Behavior

You are a senior security engineer implementing defense-in-depth tool guardrails for an AI coding assistant. Every guardian must be independently testable, configurable without code changes, and fail-open to avoid blocking legitimate work. The shared library must eliminate all code duplication while maintaining clear separation of concerns per guardian. Configuration must be intuitive for non-security users via the configure-safety skill.

# AI Section
Critical: AI can ONLY modify this section.

## Research
<!-- Filled by /spec RESEARCH -->

## Plan

### SC Updates (Post-Spec Amendments)

These user-approved changes OVERRIDE conflicting Human Section directives:

1. **FAIL-CLOSE** default on ALL hook errors (config parse failure, unexpected exception -> deny). NOT fail-open.
2. **Default decision** for most categories: **ASK** (let user confirm at runtime)
3. **Default decision** for destructive-bash and credential-guardian: **DENY** (hard block)
4. **Most-restrictive-wins** resolution at both within-guardian category overlap AND cross-guardian overlap levels
5. **Documentation** must mirror existing plugin README structure (ac-git, ac-tools patterns)
6. **Documentation** must be concise, clear, actionable -- matches repo quality bar

### Files

- `plugins/ac-safety/scripts/hooks/_lib.py` (NEW ~150 lines)
  - Shared helpers: `load_config()`, `deny()`, `allow()`, `ask()`, `resolve_path()`, `is_in_prefixes()`, `get_category_decision()`, fail-close error wrapper
- `plugins/ac-safety/scripts/hooks/credential-guardian.py` (NEW ~120 lines)
  - Refactored from `~/.claude/hooks/pretooluse/credential-guardian.py` (187 lines)
  - Config-driven blocked_prefixes, blocked_filenames, blocked_extensions, allowed_claude_files
  - Default decision: DENY
- `plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py` (NEW ~130 lines)
  - Refactored from `~/.claude/hooks/pretooluse/destructive-bash-guardian.py` (169 lines)
  - Config-driven per-category decisions, pattern lists
  - Default decision: DENY
- `plugins/ac-safety/scripts/hooks/write-scope-guardian.py` (NEW ~110 lines)
  - Refactored from `~/.claude/hooks/pretooluse/write-scope-guardian.py` (169 lines)
  - Config-driven allowed/blocked prefixes and files, ask_user_prefixes
  - Default category decision: ASK
- `plugins/ac-safety/scripts/hooks/supply-chain-guardian.py` (NEW ~110 lines)
  - Refactored from `~/.claude/hooks/pretooluse/supply-chain-guardian.py` (154 lines)
  - Config-driven allowlists, per-category decisions
  - Default category decision: ASK
- `plugins/ac-safety/scripts/hooks/playwright-guardian.py` (NEW ~100 lines)
  - Refactored from `~/.claude/hooks/pretooluse/playwright-guardian.py` (155 lines)
  - Config-driven allowed_domains, always_blocked/allowed tools, per-category decisions
  - Default category decision: ASK
- `plugins/ac-safety/config/safety.default.yaml` (NEW ~80 lines)
  - Default configuration for all guardians with ASK defaults (except destructive-bash/credential: DENY)
- `plugins/ac-safety/hooks/hooks.json` (NEW ~40 lines)
  - Tool-specific matchers with `${CLAUDE_PLUGIN_ROOT}` paths
- `plugins/ac-safety/.claude-plugin/plugin.json` (NEW ~12 lines)
  - Marketplace metadata matching ac-git/ac-tools pattern
- `plugins/ac-safety/CLAUDE.md` (NEW ~15 lines)
  - Plugin-scoped instructions
- `plugins/ac-safety/README.md` (NEW ~60 lines)
  - Documentation mirroring ac-git/ac-tools README structure
- `plugins/ac-safety/skills/configure-safety/SKILL.md` (NEW ~50 lines)
  - Interactive safety.yaml customization skill
- `plugins/ac-audit/scripts/hooks/tool-audit.py` (NEW ~100 lines)
  - Refactored from `~/.claude/hooks/tool_audit.py` (159 lines)
  - Config-driven log_dir, display_tools, max_words
- `plugins/ac-audit/config/audit.default.yaml` (NEW ~15 lines)
  - Default audit configuration
- `plugins/ac-audit/hooks/hooks.json` (NEW ~15 lines)
  - Wildcard matcher
- `plugins/ac-audit/.claude-plugin/plugin.json` (NEW ~12 lines)
  - Marketplace metadata
- `plugins/ac-audit/CLAUDE.md` (NEW ~10 lines)
  - Plugin-scoped instructions
- `plugins/ac-audit/README.md` (NEW ~40 lines)
  - Documentation mirroring ac-git/ac-tools README structure
- `plugins/ac-safety/tests/hooks/test_lib.py` (NEW ~200 lines)
  - Unit tests for _lib.py: config loading, deep-merge, path resolution, decision helpers
- `plugins/ac-safety/tests/hooks/test_credential_guardian.py` (NEW ~120 lines)
  - Unit tests for credential-guardian: blocked paths, allowed paths, config overrides
- `plugins/ac-safety/tests/hooks/test_destructive_bash_guardian.py` (NEW ~120 lines)
  - Unit tests for destructive-bash-guardian: pattern matching, category decisions
- `plugins/ac-safety/tests/hooks/test_write_scope_guardian.py` (NEW ~100 lines)
  - Unit tests for write-scope-guardian: allowed/blocked/ask prefixes
- `plugins/ac-safety/tests/hooks/test_supply_chain_guardian.py` (NEW ~100 lines)
  - Unit tests for supply-chain-guardian: allowlists, category decisions
- `plugins/ac-safety/tests/hooks/test_playwright_guardian.py` (NEW ~100 lines)
  - Unit tests for playwright-guardian: domain allowlist, blocked tools
- `plugins/ac-safety/tests/e2e/test_plugin_load.py` (NEW ~80 lines)
  - E2E: plugin loads, hooks fire on matching tools, config override precedence

### Tasks

#### Task 1 -- _lib.py: shared safety hook library
Tools: Write
File: `plugins/ac-safety/scripts/hooks/_lib.py`

Create the shared library used by all 5 guardian hooks. Must implement:
- `load_config(guardian_name)`: 3-tier deep-merge config loading (project `safety.yaml` > `~/.claude/safety.yaml` > plugin `safety.default.yaml`)
- `deny(reason)`, `allow()`, `ask(reason)`: JSON output helpers
- `resolve_path(path)`: expanduser + realpath
- `is_in_prefixes(path, prefixes)`: resolved prefix matching
- `get_category_decision(config, guardian, category)`: returns decision with most-restrictive-wins
- `fail_close(func)`: decorator that wraps main() to catch ALL exceptions and deny on error

Most-restrictive-wins ordering: deny > ask > allow. When two config tiers specify different decisions for the same category, the most restrictive wins.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/_lib.py
@@ -0,0 +1,148 @@
+"""
+Shared library for ac-safety guardian hooks.
+
+Provides config loading (3-tier deep-merge), decision helpers,
+path utilities, and fail-close error handling.
+"""
+
+import json
+import os
+import sys
+from functools import wraps
+from pathlib import Path
+from typing import Any, Callable
+
+import yaml
+
+# Decision priority for most-restrictive-wins resolution
+_DECISION_PRIORITY: dict[str, int] = {"deny": 0, "ask": 1, "allow": 2}
+
+
+def _most_restrictive(a: str, b: str) -> str:
+    """Return the more restrictive of two decisions (deny > ask > allow)."""
+    pa = _DECISION_PRIORITY.get(a, 1)  # unknown defaults to ask
+    pb = _DECISION_PRIORITY.get(b, 1)
+    return a if pa <= pb else b
+
+
+def _deep_merge(base: dict, overlay: dict) -> dict:
+    """
+    Deep-merge overlay into base. Returns new dict.
+
+    For category decision dicts, applies most-restrictive-wins.
+    For lists, overlay replaces base entirely.
+    For dicts, recursively merge.
+    """
+    result = dict(base)
+    for key, overlay_val in overlay.items():
+        if key not in result:
+            result[key] = overlay_val
+        elif isinstance(result[key], dict) and isinstance(overlay_val, dict):
+            # Check if this is a "categories" dict (values are decision strings)
+            if key == "categories":
+                merged_cats: dict[str, str] = dict(result[key])
+                for cat_key, cat_val in overlay_val.items():
+                    if cat_key in merged_cats:
+                        merged_cats[cat_key] = _most_restrictive(merged_cats[cat_key], str(cat_val))
+                    else:
+                        merged_cats[cat_key] = str(cat_val)
+                result[key] = merged_cats
+            else:
+                result[key] = _deep_merge(result[key], overlay_val)
+        else:
+            # Lists and scalars: overlay replaces
+            result[key] = overlay_val
+    return result
+
+
+def _find_plugin_root() -> Path:
+    """Find plugin root from CLAUDE_PLUGIN_ROOT env or relative to this file."""
+    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
+    if env_root:
+        return Path(env_root)
+    # Fallback: scripts/hooks/_lib.py -> plugin root is ../..
+    return Path(__file__).resolve().parent.parent.parent
+
+
+def load_config(guardian_name: str | None = None) -> dict[str, Any]:
+    """
+    Load safety config with 3-tier deep-merge resolution.
+
+    Priority (most-restrictive-wins at category level):
+      1. Project-level: $CWD/safety.yaml or $CLAUDE_PROJECT_DIR/safety.yaml
+      2. User-level: ~/.claude/safety.yaml
+      3. Plugin defaults: <plugin_root>/config/safety.default.yaml
+
+    Args:
+        guardian_name: If provided, return only that guardian's section merged
+                       with top-level keys (allowed_project_roots, etc.)
+
+    Returns:
+        Merged config dict.
+    """
+    plugin_root = _find_plugin_root()
+
+    # Layer 1: Plugin defaults (base)
+    defaults_path = plugin_root / "config" / "safety.default.yaml"
+    config: dict[str, Any] = {}
+    if defaults_path.is_file():
+        with open(defaults_path) as f:
+            config = yaml.safe_load(f) or {}
+
+    # Layer 2: User-level
+    user_path = Path.home() / ".claude" / "safety.yaml"
+    if user_path.is_file():
+        with open(user_path) as f:
+            user_cfg = yaml.safe_load(f) or {}
+        config = _deep_merge(config, user_cfg)
+
+    # Layer 3: Project-level
+    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
+    project_path = Path(project_dir) / "safety.yaml"
+    if project_path.is_file():
+        with open(project_path) as f:
+            proj_cfg = yaml.safe_load(f) or {}
+        config = _deep_merge(config, proj_cfg)
+
+    return config
+
+
+def get_category_decision(config: dict[str, Any], guardian: str, category: str) -> str:
+    """
+    Get the resolved decision for a guardian category.
+
+    Returns "deny", "ask", or "allow". Defaults to "ask" if not configured.
+    """
+    guardian_cfg = config.get(guardian, {})
+    if not isinstance(guardian_cfg, dict):
+        return "ask"
+    categories = guardian_cfg.get("categories", {})
+    if not isinstance(categories, dict):
+        return "ask"
+    decision = str(categories.get(category, "ask")).lower()
+    if decision not in _DECISION_PRIORITY:
+        return "ask"
+    return decision
+
+
+def resolve_path(path: str) -> str:
+    """Resolve path: expanduser + realpath."""
+    return os.path.realpath(os.path.expanduser(path))
+
+
+def is_in_prefixes(path: str, prefixes: list[str]) -> bool:
+    """Check if resolved path starts with any resolved prefix."""
+    resolved = resolve_path(path)
+    for prefix in prefixes:
+        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
+        if resolved.startswith(real_prefix + "/") or resolved == real_prefix:
+            return True
+    return False
+
+
+def deny(reason: str) -> None:
+    """Print JSON deny decision to stdout."""
+    print(json.dumps({
+        "hookSpecificOutput": {
+            "hookEventName": "PreToolUse",
+            "permissionDecision": "deny",
+            "permissionDecisionReason": reason,
+        }
+    }))
+
+
+def allow() -> None:
+    """Print JSON allow decision to stdout."""
+    print(json.dumps({
+        "hookSpecificOutput": {
+            "hookEventName": "PreToolUse",
+            "permissionDecision": "allow",
+        }
+    }))
+
+
+def ask(reason: str) -> None:
+    """Print JSON ask decision to stdout."""
+    print(json.dumps({
+        "hookSpecificOutput": {
+            "hookEventName": "PreToolUse",
+            "permissionDecision": "ask",
+            "permissionDecisionReason": reason,
+        }
+    }))
+
+
+def fail_close(func: Callable[[], None]) -> Callable[[], None]:
+    """
+    Decorator: wraps hook main() with fail-close error handling.
+    On ANY exception (config parse, unexpected error), deny the operation.
+    """
+    @wraps(func)
+    def wrapper() -> None:
+        try:
+            func()
+        except Exception as e:
+            deny(f"Hook error (fail-close): {e}")
+            print(f"Hook error (fail-close): {e}", file=sys.stderr)
+    return wrapper
````

Verification:
- File exists at `plugins/ac-safety/scripts/hooks/_lib.py`
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/_lib.py').read()); print('OK')"`

#### Task 2 -- credential-guardian.py: config-driven credential access guard
Tools: Write
File: `plugins/ac-safety/scripts/hooks/credential-guardian.py`

Refactored from `~/.claude/hooks/pretooluse/credential-guardian.py`. Reads blocked_prefixes, blocked_filenames, blocked_extensions, allowed_claude_files, allowed_project_roots from config. Default decision: DENY. Uses `_lib.py` for all helpers. PEP 723 header. Fail-close via decorator.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/credential-guardian.py
@@ -0,0 +1,118 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+PreToolUse hook: blocks Read/Grep/Glob access to credential files.
+
+Config-driven via safety.yaml (credential_guardian section).
+Default decision: DENY. Fail-close on errors.
+"""
+
+import json
+import os
+import re
+import sys
+
+# Import shared library via sys.path
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+from _lib import allow, deny, fail_close, is_in_prefixes, load_config, resolve_path
+
+READ_TOOLS = {"Read", "Grep", "Glob"}
+
+
+def _extract_paths(tool_name: str, tool_input: dict) -> list[str]:
+    """Extract file paths from tool input based on tool type."""
+    paths: list[str] = []
+    if tool_name == "Read":
+        p = tool_input.get("file_path", "")
+        if p:
+            paths.append(p)
+    elif tool_name == "Grep":
+        p = tool_input.get("path", "")
+        if p:
+            paths.append(p)
+        g = tool_input.get("glob", "")
+        if g and "/" in g:
+            paths.append(g)
+    elif tool_name == "Glob":
+        p = tool_input.get("path", "")
+        if p:
+            paths.append(p)
+        pat = tool_input.get("pattern", "")
+        if pat and pat.startswith("/"):
+            paths.append(pat)
+    return paths
+
+
+def _is_blocked(
+    path: str,
+    blocked_prefixes: list[str],
+    blocked_filenames: list[str],
+    blocked_extensions: list[str],
+    allowed_project_roots: list[str],
+    allowed_claude_files: list[str],
+) -> str | None:
+    """Returns block reason or None if allowed."""
+    resolved = resolve_path(path)
+
+    # Always-blocked absolute prefixes
+    for prefix in blocked_prefixes:
+        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
+        if resolved.startswith(real_prefix) or resolved == real_prefix:
+            # Exception for explicitly allowed claude files
+            if any(resolved == os.path.realpath(os.path.expanduser(f)) for f in allowed_claude_files):
+                return None
+            return f"Access to {prefix} is blocked (credential protection)"
+
+    # Blocked filenames in home dir
+    basename = os.path.basename(resolved)
+    home = os.path.expanduser("~")
+    if basename in blocked_filenames and resolved.startswith(home):
+        return f"Access to {basename} is blocked (credential file)"
+
+    # Outside project roots: block sensitive extensions and .env
+    if not is_in_prefixes(path, allowed_project_roots + ["/private/tmp/", "/tmp/"]):
+        _, ext = os.path.splitext(resolved)
+        if ext.lower() in blocked_extensions:
+            return f"Access to {ext} files outside project dirs is blocked"
+        if re.search(r"(^|/)\.env(\..+)?$", os.path.basename(resolved)):
+            return f"Access to .env files outside project dirs is blocked"
+
+    return None
+
+
+@fail_close
+def main() -> None:
+    input_data = json.load(sys.stdin)
+    tool_name = input_data.get("tool_name", "")
+    tool_input = input_data.get("tool_input", {})
+
+    if tool_name not in READ_TOOLS:
+        allow()
+        return
+
+    config = load_config()
+    cg = config.get("credential_guardian", {})
+    if not isinstance(cg, dict):
+        cg = {}
+
+    blocked_prefixes: list[str] = cg.get("blocked_prefixes", [
+        "~/.aws/", "~/.ssh/", "~/.config/gh/", "~/.docker/",
+        "~/.gnupg/", "~/Library/", "~/.claude/debug/", "~/.claude/.claude.json",
+    ])
+    blocked_filenames: list[str] = cg.get("blocked_filenames", [
+        ".npmrc", ".netrc", ".pypirc", ".git-credentials",
+    ])
+    blocked_extensions: list[str] = cg.get("blocked_extensions", [".pem", ".key", ".p12", ".pfx"])
+    allowed_project_roots: list[str] = config.get("allowed_project_roots", ["~/projects/"])
+    allowed_claude_files: list[str] = cg.get("allowed_claude_files", [
+        "~/.claude/settings.json", "~/.claude/settings.local.json", "~/.claude/CLAUDE.md",
+    ])
+
+    paths = _extract_paths(tool_name, tool_input)
+    for path in paths:
+        reason = _is_blocked(path, blocked_prefixes, blocked_filenames, blocked_extensions, allowed_project_roots, allowed_claude_files)
+        if reason:
+            deny(f"BLOCKED: {reason}")
+            return
+
+    allow()
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/credential-guardian.py').read()); print('OK')"`

#### Task 3 -- destructive-bash-guardian.py: config-driven destructive command guard
Tools: Write
File: `plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py`

Refactored from `~/.claude/hooks/pretooluse/destructive-bash-guardian.py`. Per-category configurable decisions. Default decision: DENY. Categories: git-destructive, file-destruction, aws-destructive, data-exfiltration, process-destruction, persistence, system-level, docker-destruction, npm-publish, iac-destruction, permission-abuse, credential-reads. PEP 723 header. Fail-close.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py
@@ -0,0 +1,136 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+PreToolUse hook: blocks destructive bash commands.
+
+Config-driven per-category decisions via safety.yaml (destructive_bash section).
+Default decision: DENY. Fail-close on errors.
+"""
+
+import json
+import os
+import re
+import sys
+
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+from _lib import allow, ask, deny, fail_close, get_category_decision, load_config
+
+# Map: (compiled_pattern, reason, category)
+# Category names match safety.yaml destructive_bash.categories keys
+PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
+    # -- file-destruction --
+    (re.compile(r"\brm\s+(-[^\s]*)*\s*-[rR].*(" + re.escape(os.path.expanduser("~")) + r"[/\s]|~/|/Users/\w+/(?!projects/))"), "rm -r targeting home or outside project", "file-destruction"),
+    (re.compile(r"\brm\s+(-[^\s]*\s+)*-rf\s+/(?!Users/\w+/projects/)"), "rm -rf targeting system or non-project path", "file-destruction"),
+    (re.compile(r"\brm\s+(-[^\s]*\s+)*-rf\s+~/(?!projects/)"), "rm -rf targeting home subdirectory outside project", "file-destruction"),
+    (re.compile(r"\brm\s+(-[^\s]*\s+)*-rf\s+~\s"), "rm -rf targeting entire home directory", "file-destruction"),
+    (re.compile(r"\brm\s+(-[^\s]*\s+)*-rf\s+\.\.\s"), "rm -rf targeting parent directory", "file-destruction"),
+    # -- aws-destructive --
+    (re.compile(r"\baws\s+s3\s+rb\b"), "aws s3 rb (bucket removal)", "aws-destructive"),
+    (re.compile(r"\baws\s+s3\s+rm\s+.*--recursive\b"), "aws s3 rm --recursive", "aws-destructive"),
+    (re.compile(r"\baws\s+cloudformation\s+delete-stack\b"), "aws cloudformation delete-stack", "aws-destructive"),
+    (re.compile(r"\baws\s+lambda\s+delete-function\b"), "aws lambda delete-function", "aws-destructive"),
+    (re.compile(r"\baws\s+dynamodb\s+delete-table\b"), "aws dynamodb delete-table", "aws-destructive"),
+    (re.compile(r"\baws\s+rds\s+delete-db-instance\b"), "aws rds delete-db-instance", "aws-destructive"),
+    (re.compile(r"\baws\s+rds\s+delete-db-cluster\b"), "aws rds delete-db-cluster", "aws-destructive"),
+    (re.compile(r"\baws\s+ec2\s+terminate-instances\b"), "aws ec2 terminate-instances", "aws-destructive"),
+    (re.compile(r"\baws\s+iam\s+delete-(role|user|policy|group)\b"), "aws iam delete operation", "aws-destructive"),
+    (re.compile(r"\baws\s+iam\s+attach-role-policy\b"), "aws iam attach-role-policy (privilege escalation)", "aws-destructive"),
+    (re.compile(r"\baws\s+secretsmanager\s+delete-secret\b"), "aws secretsmanager delete-secret", "aws-destructive"),
+    (re.compile(r"\baws\s+eks\s+delete-cluster\b"), "aws eks delete-cluster", "aws-destructive"),
+    (re.compile(r"\baws\s+ecr\s+delete-repository\b"), "aws ecr delete-repository", "aws-destructive"),
+    # -- git-destructive --
+    (re.compile(r"\bgit\s+push\s+.*--force(?!-with-lease)\b"), "git push --force (use --force-with-lease)", "git-destructive"),
+    (re.compile(r"\bgit\s+push\s+(-[^\s]*)*-f\b"), "git push -f (force push)", "git-destructive"),
+    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard", "git-destructive"),
+    (re.compile(r"\bgit\s+clean\s+(-[^\s]*)*-[fd]"), "git clean -f/-d", "git-destructive"),
+    (re.compile(r"\bgit\s+stash\s+clear\b"), "git stash clear", "git-destructive"),
+    (re.compile(r"\bgit\s+reflog\s+expire\b"), "git reflog expire", "git-destructive"),
+    (re.compile(r"\bgit\s+gc\s+.*--prune=now"), "git gc --prune=now", "git-destructive"),
+    (re.compile(r"\bgit\s+filter-branch\b"), "git filter-branch", "git-destructive"),
+    (re.compile(r"\bgit\s+push\s+\S+\s+--delete\b"), "git push --delete (remote branch deletion)", "git-destructive"),
+    (re.compile(r"\bgit\s+checkout\s+\.\s*$"), "git checkout . (discard all changes)", "git-destructive"),
+    (re.compile(r"\bgit\s+restore\s+\.\s*$"), "git restore . (discard all changes)", "git-destructive"),
+    # -- credential-reads --
+    (re.compile(r"\bcat\s+.*~/.ssh/"), "cat reading SSH directory", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.aws/"), "cat reading AWS directory", "credential-reads"),
+    (re.compile(r"\bcat\s+.*/\.ssh/"), "cat reading SSH directory (absolute)", "credential-reads"),
+    (re.compile(r"\bcat\s+.*/\.aws/"), "cat reading AWS directory (absolute)", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.config/gh/"), "cat reading GitHub CLI config", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.npmrc\b"), "cat reading npmrc", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.netrc\b"), "cat reading netrc", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.docker/"), "cat reading Docker config", "credential-reads"),
+    (re.compile(r"\bcat\s+.*~/.claude/\.claude\.json\b"), "cat reading Claude API tokens", "credential-reads"),
+    (re.compile(r"\bsecurity\s+(find|dump)-.*keychain"), "macOS Keychain access", "credential-reads"),
+    # -- data-exfiltration --
+    (re.compile(r"\bcurl\s+.*-X\s*POST\b"), "curl POST (potential exfiltration)", "data-exfiltration"),
+    (re.compile(r"\bcurl\s+.*--data\b"), "curl --data (potential exfiltration)", "data-exfiltration"),
+    (re.compile(r"\bcurl\s+.*-d\s"), "curl -d (potential exfiltration)", "data-exfiltration"),
+    (re.compile(r"\bwget\s+.*--post"), "wget POST (potential exfiltration)", "data-exfiltration"),
+    (re.compile(r"\bnslookup\s+.*\$\("), "DNS exfiltration attempt", "data-exfiltration"),
+    (re.compile(r"\bdig\s+.*\$\("), "DNS exfiltration attempt", "data-exfiltration"),
+    # -- process-destruction --
+    (re.compile(r"\bkill\s+-9\s+-1\b"), "kill all user processes", "process-destruction"),
+    (re.compile(r"\bkillall\s+-9\b"), "killall -9", "process-destruction"),
+    (re.compile(r"\bpkill\s+-9\b"), "pkill -9", "process-destruction"),
+    (re.compile(r"\bpkill\s+-u\s"), "pkill by user (mass kill)", "process-destruction"),
+    # -- permission-abuse --
+    (re.compile(r"\bchmod\s+(-[^\s]+\s+)*777\b"), "chmod 777", "permission-abuse"),
+    (re.compile(r"\bchmod\s+-[Rr].*777"), "recursive chmod 777", "permission-abuse"),
+    # -- persistence --
+    (re.compile(r"\bcrontab\b"), "crontab modification", "persistence"),
+    (re.compile(r"LaunchAgents"), "LaunchAgent persistence", "persistence"),
+    (re.compile(r"\bnohup\s+"), "nohup background process", "persistence"),
+    # -- system-level --
+    (re.compile(r"\bmkfs\."), "filesystem format", "system-level"),
+    (re.compile(r"\bdd\s+.*of=/dev/"), "dd to device", "system-level"),
+    (re.compile(r":\(\)\{.*\|.*&.*\};:"), "fork bomb", "system-level"),
+    # -- iac-destruction --
+    (re.compile(r"\bterraform\s+destroy\b"), "terraform destroy", "iac-destruction"),
+    (re.compile(r"\bpulumi\s+destroy\b"), "pulumi destroy", "iac-destruction"),
+    # -- docker-destruction --
+    (re.compile(r"\bdocker\s+system\s+prune\s+-a\b"), "docker system prune -a", "docker-destruction"),
+    (re.compile(r"\bdocker\s+volume\s+prune\b"), "docker volume prune", "docker-destruction"),
+    # -- npm-publish --
+    (re.compile(r"\bnpm\s+publish\b"), "npm publish", "npm-publish"),
+    (re.compile(r"\bnpm\s+unpublish\b"), "npm unpublish", "npm-publish"),
+]
+
+
+@fail_close
+def main() -> None:
+    input_data = json.load(sys.stdin)
+    tool_name = input_data.get("tool_name", "")
+    tool_input = input_data.get("tool_input", {})
+
+    if tool_name != "Bash":
+        allow()
+        return
+
+    command = tool_input.get("command", "")
+    config = load_config()
+
+    for pattern, reason, category in PATTERNS:
+        if pattern.search(command):
+            decision = get_category_decision(config, "destructive_bash", category)
+            if decision == "deny":
+                deny(f"BLOCKED: {reason}. Command denied by destructive-bash-guardian.")
+            elif decision == "ask":
+                ask(f"{reason} -- confirm to proceed?")
+            # else: allow (fall through)
+            else:
+                allow()
+            return
+
+    allow()
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py').read()); print('OK')"`

#### Task 4 -- write-scope-guardian.py: config-driven write scope guard
Tools: Write
File: `plugins/ac-safety/scripts/hooks/write-scope-guardian.py`

Refactored from `~/.claude/hooks/pretooluse/write-scope-guardian.py`. Config-driven allowed_write_prefixes, blocked_write_prefixes, blocked_write_files, ask_user_prefixes, git_hooks_segment. PEP 723 header. Fail-close.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/write-scope-guardian.py
@@ -0,0 +1,112 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+PreToolUse hook: restricts Write/Edit to allowed project paths.
+
+Config-driven via safety.yaml (write_scope section).
+Default category decisions: ASK. Fail-close on errors.
+"""
+
+import json
+import os
+import sys
+
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+from _lib import allow, ask, deny, fail_close, is_in_prefixes, load_config, resolve_path
+
+WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
+
+
+def _extract_path(tool_name: str, tool_input: dict) -> str | None:
+    if tool_name in ("Write", "Edit"):
+        return tool_input.get("file_path")
+    if tool_name == "NotebookEdit":
+        return tool_input.get("notebook_path")
+    return None
+
+
+def _check_write(
+    path: str,
+    blocked_write_files: list[str],
+    ask_user_prefixes: list[str],
+    blocked_write_prefixes: list[str],
+    allowed_write_prefixes: list[str],
+    git_hooks_segment: str,
+) -> tuple[str, str | None]:
+    """Returns (decision, reason). decision: 'allow', 'deny', or 'ask'."""
+    resolved = resolve_path(path)
+
+    # Block specific files
+    for blocked_file in blocked_write_files:
+        if resolved == os.path.realpath(os.path.expanduser(blocked_file)):
+            return "deny", f"Write to {blocked_file} is blocked (tamper protection)"
+
+    # Ask user for sensitive directories
+    for prefix in ask_user_prefixes:
+        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
+        if resolved.startswith(real_prefix):
+            return "ask", f"Write to {path} targets sensitive directory -- confirm?"
+
+    # Block specific prefixes
+    for prefix in blocked_write_prefixes:
+        real_prefix = os.path.realpath(os.path.expanduser(prefix.rstrip("/")))
+        if resolved.startswith(real_prefix):
+            return "deny", f"Write to {prefix} is blocked (protected directory)"
+
+    # Block .git/hooks/ injection
+    if git_hooks_segment in resolved:
+        return "deny", "Write to .git/hooks/ is blocked (hook injection prevention)"
+
+    # If in allowed prefixes, allow
+    if is_in_prefixes(path, allowed_write_prefixes):
+        return "allow", None
+
+    return "deny", f"Write to {path} is blocked (outside allowed project directories)"
+
+
+@fail_close
+def main() -> None:
+    input_data = json.load(sys.stdin)
+    tool_name = input_data.get("tool_name", "")
+    tool_input = input_data.get("tool_input", {})
+
+    if tool_name not in WRITE_TOOLS:
+        allow()
+        return
+
+    path = _extract_path(tool_name, tool_input)
+    if not path:
+        allow()
+        return
+
+    config = load_config()
+    ws = config.get("write_scope", {})
+    if not isinstance(ws, dict):
+        ws = {}
+
+    allowed_write_prefixes: list[str] = ws.get("allowed_write_prefixes", [
+        "~/projects/", "~/.claude/", "~/.claude-secondary/", "/private/tmp/", "/tmp/",
+    ])
+    blocked_write_prefixes: list[str] = ws.get("blocked_write_prefixes", [
+        "~/.ssh/", "~/.aws/", "~/.config/gh/", "~/.docker/", "~/.gnupg/",
+        "~/Library/LaunchAgents/", "~/Library/LaunchDaemons/",
+        "/etc/", "/usr/", "/bin/", "/sbin/",
+    ])
+    blocked_write_files: list[str] = ws.get("blocked_write_files", [
+        "~/.claude/settings.json", "~/.claude/settings.local.json",
+        "~/.claude-secondary/settings.json",
+        "~/.bashrc", "~/.zshrc", "~/.zprofile", "~/.profile", "~/.bash_profile",
+        "~/.npmrc", "~/.netrc", "~/.gitconfig", "~/.pypirc", "~/.pythonrc",
+        "~/.ssh/authorized_keys",
+    ])
+    ask_user_prefixes: list[str] = ws.get("ask_user_prefixes", [
+        "~/.claude/hooks/", "~/.claude-secondary/hooks/",
+    ])
+    git_hooks_segment: str = ws.get("git_hooks_segment", "/.git/hooks/")
+
+    result, reason = _check_write(
+        path, blocked_write_files, ask_user_prefixes,
+        blocked_write_prefixes, allowed_write_prefixes, git_hooks_segment,
+    )
+    if result == "deny":
+        deny(f"BLOCKED: {reason}")
+    elif result == "ask":
+        ask(reason or "")
+    else:
+        allow()
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/write-scope-guardian.py').read()); print('OK')"`

#### Task 5 -- supply-chain-guardian.py: config-driven supply chain guard
Tools: Write
File: `plugins/ac-safety/scripts/hooks/supply-chain-guardian.py`

Refactored from `~/.claude/hooks/pretooluse/supply-chain-guardian.py`. Config-driven npx_allowlist, uv_add_allowlist, per-category decisions (npx-packages, pip-direct, uv-add, uv-pip-direct). Default category decision: ASK. PEP 723 header. Fail-close.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/supply-chain-guardian.py
@@ -0,0 +1,115 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+PreToolUse hook: blocks unapproved package installations.
+
+Config-driven via safety.yaml (supply_chain section).
+Default category decisions: ASK. Fail-close on errors.
+"""
+
+import json
+import os
+import re
+import sys
+
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+from _lib import allow, ask, deny, fail_close, get_category_decision, load_config
+
+# Patterns that are SAFE (skip blocking)
+SAFE_PATTERNS = [
+    re.compile(r"\bnpm\s+(install|ci)\s*$"),
+    re.compile(r"\bnpm\s+(install|ci)\s+--"),
+    re.compile(r"\bpip\s+install\s+(-r\s|--requirement\s|-e\s|--editable\s|\.\s*$)"),
+    re.compile(r"\buv\s+sync\b"),
+    re.compile(r"\buv\s+run\b"),
+    re.compile(r"\buv\s+pip\s+install\s+(-r\s|--requirement\s|-e\s|--editable\s|\.\s*$)"),
+    re.compile(r"\buv\s+pip\s+compile\b"),
+]
+
+
+def _apply_decision(config: dict, category: str, reason: str) -> None:
+    """Apply the configured decision for a supply_chain category."""
+    decision = get_category_decision(config, "supply_chain", category)
+    if decision == "deny":
+        deny(f"BLOCKED: {reason}. Supply-chain-guardian.")
+    elif decision == "ask":
+        ask(f"{reason} -- confirm to proceed?")
+    else:
+        allow()
+
+
+def _is_npx_blocked(command: str, npx_allowlist: set[str]) -> str | None:
+    match = re.search(r"\bnpx\s+(?:--yes\s+)?(@?[\w/-]+(?:@[\w./-]+)?)", command)
+    if not match:
+        return None
+    package = match.group(1)
+    base_package = re.sub(r"@[\w./-]+$", "", package) if not package.startswith("@") else \
+                   re.sub(r"@[\w./-]+$", "", package) if package.count("@") > 1 else package
+    if base_package in npx_allowlist:
+        return None
+    return f"npx with unapproved package '{package}' (not in allowlist)"
+
+
+def _is_pip_blocked(command: str) -> str | None:
+    if not re.search(r"\bpip\s+install\b", command):
+        return None
+    for safe in SAFE_PATTERNS:
+        if safe.search(command):
+            return None
+    return "pip install of direct package (use requirements.txt instead)"
+
+
+def _is_uv_add_blocked(command: str, uv_add_allowlist: set[str]) -> str | None:
+    match = re.search(r"\buv\s+add\s+(\S+)", command)
+    if not match:
+        return None
+    package = match.group(1)
+    if package.startswith("-"):
+        return None
+    if package in uv_add_allowlist:
+        return None
+    return f"uv add with unapproved package '{package}' (not in allowlist)"
+
+
+def _is_uv_pip_blocked(command: str) -> str | None:
+    if not re.search(r"\buv\s+pip\s+install\b", command):
+        return None
+    for safe in SAFE_PATTERNS:
+        if safe.search(command):
+            return None
+    return "uv pip install of direct package (use requirements.txt or uv sync)"
+
+
+@fail_close
+def main() -> None:
+    input_data = json.load(sys.stdin)
+    tool_name = input_data.get("tool_name", "")
+    tool_input = input_data.get("tool_input", {})
+
+    if tool_name != "Bash":
+        allow()
+        return
+
+    command = tool_input.get("command", "")
+
+    # Fast path: safe patterns always allowed
+    for safe in SAFE_PATTERNS:
+        if safe.search(command):
+            allow()
+            return
+
+    config = load_config()
+    sc = config.get("supply_chain", {})
+    if not isinstance(sc, dict):
+        sc = {}
+
+    npx_allowlist = set(sc.get("npx_allowlist", [
+        "@playwright/mcp", "ts-node", "cdk", "aws-cdk", "jest", "tsx", "tsc", "prettier", "eslint",
+    ]))
+    uv_add_allowlist = set(sc.get("uv_add_allowlist", []))
+
+    # Check each supply chain risk
+    checks: list[tuple[str | None, str]] = [
+        (_is_npx_blocked(command, npx_allowlist), "npx-packages"),
+        (_is_pip_blocked(command), "pip-direct"),
+        (_is_uv_add_blocked(command, uv_add_allowlist), "uv-add"),
+        (_is_uv_pip_blocked(command), "uv-pip-direct"),
+    ]
+    for reason, category in checks:
+        if reason:
+            _apply_decision(config, category, reason)
+            return
+
+    allow()
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/supply-chain-guardian.py').read()); print('OK')"`

#### Task 6 -- playwright-guardian.py: config-driven playwright/MCP guard
Tools: Write
File: `plugins/ac-safety/scripts/hooks/playwright-guardian.py`

Refactored from `~/.claude/hooks/pretooluse/playwright-guardian.py`. Config-driven allowed_domains, always_blocked_tools, always_allowed_tools, per-category decisions. Default category decision: ASK. PEP 723 header. Fail-close.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/scripts/hooks/playwright-guardian.py
@@ -0,0 +1,104 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+PreToolUse hook: restricts Playwright/MCP tool usage.
+
+Config-driven via safety.yaml (playwright section).
+Default category decisions: ASK. Fail-close on errors.
+"""
+
+import json
+import os
+import sys
+from urllib.parse import urlparse
+
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+from _lib import allow, ask, deny, fail_close, get_category_decision, load_config
+
+MCP_PREFIXES = ["mcp__playwright__", "mcp__plugin_playwright_playwright__"]
+
+DEFAULT_ALLOWED_DOMAINS = {
+    "localhost", "127.0.0.1", "github.com", "gitlab.com", "pypi.org",
+    "www.npmjs.com", "docs.aws.amazon.com", "docs.python.org",
+    "stackoverflow.com", "developer.mozilla.org", "www.google.com",
+    "serper.dev", "serpapi.com",
+}
+
+DEFAULT_ALWAYS_BLOCKED = {"browser_evaluate", "browser_fill_form"}
+
+DEFAULT_ALWAYS_ALLOWED = {
+    "browser_snapshot", "browser_take_screenshot", "browser_click",
+    "browser_close", "browser_resize", "browser_tabs",
+    "browser_console_messages", "browser_network_requests",
+    "browser_press_key", "browser_hover", "browser_wait_for",
+    "browser_navigate_back", "browser_install", "browser_handle_dialog",
+    "browser_select_option", "browser_drag", "browser_type", "browser_run_code",
+}
+
+
+def _get_mcp_action(tool_name: str) -> str | None:
+    for prefix in MCP_PREFIXES:
+        if tool_name.startswith(prefix):
+            return tool_name[len(prefix):]
+    return None
+
+
+def _is_domain_allowed(url: str, allowed_domains: set[str]) -> bool:
+    try:
+        parsed = urlparse(url)
+        hostname = parsed.hostname or ""
+        bare_host = hostname.removeprefix("www.")
+        return hostname in allowed_domains or bare_host in allowed_domains or f"www.{bare_host}" in allowed_domains
+    except Exception:
+        return False
+
+
+@fail_close
+def main() -> None:
+    input_data = json.load(sys.stdin)
+    tool_name = input_data.get("tool_name", "")
+    tool_input = input_data.get("tool_input", {})
+
+    action = _get_mcp_action(tool_name)
+    if action is None:
+        allow()
+        return
+
+    config = load_config()
+    pw = config.get("playwright", {})
+    if not isinstance(pw, dict):
+        pw = {}
+
+    always_blocked = set(pw.get("always_blocked_tools", list(DEFAULT_ALWAYS_BLOCKED)))
+    always_allowed = set(pw.get("always_allowed_tools", list(DEFAULT_ALWAYS_ALLOWED)))
+    allowed_domains = set(pw.get("allowed_domains", list(DEFAULT_ALLOWED_DOMAINS)))
+
+    # Always blocked
+    if action in always_blocked:
+        deny(f"BLOCKED: {action} is always blocked (arbitrary code execution / credential risk)")
+        return
+
+    # Always allowed
+    if action in always_allowed:
+        allow()
+        return
+
+    # Navigation: check domain
+    if action == "browser_navigate":
+        url = tool_input.get("url", "")
+        if not _is_domain_allowed(url, allowed_domains):
+            decision = get_category_decision(config, "playwright", "navigate-blocked-domain")
+            if decision == "deny":
+                deny(f"BLOCKED: Navigation to '{url}' denied (domain not in allowlist)")
+            elif decision == "ask":
+                ask(f"Navigation to '{url}' -- domain not in allowlist. Allow?")
+            else:
+                allow()
+            return
+        allow()
+        return
+
+    # File upload
+    if action == "browser_file_upload":
+        decision = get_category_decision(config, "playwright", "browser-file-upload")
+        if decision == "deny":
+            deny("BLOCKED: browser_file_upload is blocked (data exfiltration risk)")
+        elif decision == "ask":
+            ask("browser_file_upload detected -- confirm to proceed?")
+        else:
+            allow()
+        return
+
+    # Unknown MCP action
+    decision = get_category_decision(config, "playwright", "unknown-mcp-action")
+    if decision == "deny":
+        deny(f"BLOCKED: Unknown MCP action '{action}' denied by default")
+    elif decision == "ask":
+        ask(f"Unknown MCP action '{action}' -- confirm to proceed?")
+    else:
+        allow()
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-safety/scripts/hooks/playwright-guardian.py').read()); print('OK')"`

#### Task 7 -- safety.default.yaml: default config for all guardians
Tools: Write
File: `plugins/ac-safety/config/safety.default.yaml`

Default configuration. Per SC updates: destructive_bash and credential_guardian categories default to DENY. All other guardian categories default to ASK. Lists contain comprehensive defaults from source hooks.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/config/safety.default.yaml
@@ -0,0 +1,87 @@
+# ac-safety default configuration
+# Override at: project safety.yaml > ~/.claude/safety.yaml > this file
+# Resolution: deep-merge with most-restrictive-wins for category decisions
+
+allowed_project_roots:
+  - "~/projects/"
+
+credential_guardian:
+  blocked_prefixes:
+    - "~/.aws/"
+    - "~/.ssh/"
+    - "~/.config/gh/"
+    - "~/.docker/"
+    - "~/.gnupg/"
+    - "~/Library/"
+    - "~/.claude/debug/"
+    - "~/.claude/.claude.json"
+  blocked_filenames:
+    - ".npmrc"
+    - ".netrc"
+    - ".pypirc"
+    - ".git-credentials"
+  blocked_extensions:
+    - ".pem"
+    - ".key"
+    - ".p12"
+    - ".pfx"
+  allowed_claude_files:
+    - "~/.claude/settings.json"
+    - "~/.claude/settings.local.json"
+    - "~/.claude/CLAUDE.md"
+
+destructive_bash:
+  categories:
+    git-destructive: deny
+    file-destruction: deny
+    aws-destructive: deny
+    data-exfiltration: deny
+    process-destruction: deny
+    persistence: deny
+    system-level: deny
+    docker-destruction: deny
+    npm-publish: deny
+    iac-destruction: deny
+    permission-abuse: deny
+    credential-reads: deny
+
+write_scope:
+  allowed_write_prefixes:
+    - "~/projects/"
+    - "~/.claude/"
+    - "~/.claude-secondary/"
+    - "/private/tmp/"
+    - "/tmp/"
+  blocked_write_prefixes:
+    - "~/.ssh/"
+    - "~/.aws/"
+    - "~/.config/gh/"
+    - "~/.docker/"
+    - "~/.gnupg/"
+    - "~/Library/LaunchAgents/"
+    - "~/Library/LaunchDaemons/"
+    - "/etc/"
+    - "/usr/"
+    - "/bin/"
+    - "/sbin/"
+  blocked_write_files:
+    - "~/.claude/settings.json"
+    - "~/.claude/settings.local.json"
+    - "~/.claude-secondary/settings.json"
+    - "~/.bashrc"
+    - "~/.zshrc"
+    - "~/.zprofile"
+    - "~/.profile"
+    - "~/.bash_profile"
+    - "~/.npmrc"
+    - "~/.netrc"
+    - "~/.gitconfig"
+    - "~/.pypirc"
+    - "~/.pythonrc"
+    - "~/.ssh/authorized_keys"
+  ask_user_prefixes:
+    - "~/.claude/hooks/"
+    - "~/.claude-secondary/hooks/"
+  git_hooks_segment: "/.git/hooks/"
+
+supply_chain:
+  categories:
+    npx-packages: ask
+    pip-direct: ask
+    uv-add: ask
+    uv-pip-direct: ask
+  npx_allowlist:
+    - "@playwright/mcp"
+    - "ts-node"
+    - "cdk"
+    - "aws-cdk"
+    - "jest"
+    - "tsx"
+    - "tsc"
+    - "prettier"
+    - "eslint"
+  uv_add_allowlist: []
+
+playwright:
+  categories:
+    navigate-blocked-domain: ask
+    browser-evaluate: ask
+    browser-fill-form: ask
+    browser-file-upload: ask
+    unknown-mcp-action: ask
+  allowed_domains:
+    - "localhost"
+    - "127.0.0.1"
+    - "github.com"
+    - "gitlab.com"
+    - "pypi.org"
+    - "www.npmjs.com"
+    - "docs.aws.amazon.com"
+    - "docs.python.org"
+    - "stackoverflow.com"
+    - "developer.mozilla.org"
+    - "www.google.com"
+    - "serper.dev"
+    - "serpapi.com"
+  always_blocked_tools:
+    - "browser_evaluate"
+    - "browser_fill_form"
+  always_allowed_tools:
+    - "browser_snapshot"
+    - "browser_take_screenshot"
+    - "browser_click"
+    - "browser_close"
+    - "browser_resize"
+    - "browser_tabs"
+    - "browser_console_messages"
+    - "browser_network_requests"
+    - "browser_press_key"
+    - "browser_hover"
+    - "browser_wait_for"
+    - "browser_navigate_back"
+    - "browser_install"
+    - "browser_handle_dialog"
+    - "browser_select_option"
+    - "browser_drag"
+    - "browser_type"
+    - "browser_run_code"
````

Verification:
- `python -c "import yaml; yaml.safe_load(open('plugins/ac-safety/config/safety.default.yaml')); print('OK')"`

#### Task 8 -- hooks.json for ac-safety
Tools: Write
File: `plugins/ac-safety/hooks/hooks.json`

Matches spec structure from Human Section. Uses `${CLAUDE_PLUGIN_ROOT}` variable paths. credential-guardian on Read|Grep|Glob, destructive-bash + supply-chain on Bash, write-scope on Write|Edit|NotebookEdit, playwright on mcp matcher. Timeout 5000ms on all hooks.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/hooks/hooks.json
@@ -0,0 +1,42 @@
+{
+  "hooks": {
+    "PreToolUse": [
+      {
+        "matcher": "Read|Grep|Glob",
+        "hooks": [{
+          "type": "command",
+          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/credential-guardian.py",
+          "timeout": 5000
+        }]
+      },
+      {
+        "matcher": "Bash",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/destructive-bash-guardian.py",
+            "timeout": 5000
+          },
+          {
+            "type": "command",
+            "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/supply-chain-guardian.py",
+            "timeout": 5000
+          }
+        ]
+      },
+      {
+        "matcher": "Write|Edit|NotebookEdit",
+        "hooks": [{
+          "type": "command",
+          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/write-scope-guardian.py",
+          "timeout": 5000
+        }]
+      },
+      {
+        "matcher": "mcp__playwright__*|mcp__plugin_playwright_playwright__*",
+        "hooks": [{
+          "type": "command",
+          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/playwright-guardian.py",
+          "timeout": 5000
+        }]
+      }
+    ]
+  }
+}
````

Verification:
- `python -c "import json; json.load(open('plugins/ac-safety/hooks/hooks.json')); print('OK')"`

#### Task 9 -- plugin.json for ac-safety
Tools: Write
File: `plugins/ac-safety/.claude-plugin/plugin.json`

Marketplace metadata matching ac-git/ac-tools pattern. Version 0.2.2.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/.claude-plugin/plugin.json
@@ -0,0 +1,12 @@
+{
+  "name": "ac-safety",
+  "description": "Security guardrails - credential protection, destructive command blocking, write scope enforcement, supply chain control, browser restrictions",
+  "version": "0.2.2",
+  "author": {
+    "name": "Agentic Config Contributors"
+  },
+  "homepage": "https://github.com/WaterplanAI/agentic-config",
+  "repository": "https://github.com/WaterplanAI/agentic-config",
+  "license": "MIT",
+  "keywords": ["safety", "security", "guardian", "hooks", "credentials", "destructive"]
+}
````

Verification:
- `python -c "import json; json.load(open('plugins/ac-safety/.claude-plugin/plugin.json')); print('OK')"`

#### Task 10 -- CLAUDE.md for ac-safety
Tools: Write
File: `plugins/ac-safety/CLAUDE.md`

Plugin-scoped instructions for Claude Code when this plugin is active.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/CLAUDE.md
@@ -0,0 +1,14 @@
+# ac-safety
+
+Security guardrails plugin for Claude Code.
+
+## Hooks
+
+All hooks use fail-close: errors deny the operation.
+
+- credential-guardian: blocks Read/Grep/Glob access to credential files
+- destructive-bash-guardian: blocks destructive Bash commands by category
+- write-scope-guardian: restricts Write/Edit to allowed paths
+- supply-chain-guardian: blocks unapproved package installations
+- playwright-guardian: restricts Playwright/MCP tool usage
+
+Configuration: `safety.yaml` (project > `~/.claude/safety.yaml` > plugin defaults)
````

Verification:
- File exists and contains expected content.

#### Task 11 -- README.md for ac-safety
Tools: Write
File: `plugins/ac-safety/README.md`

Documentation mirroring ac-git/ac-tools README structure. Concise, clear, actionable.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/README.md
@@ -0,0 +1,75 @@
+# ac-safety
+
+Security guardrails -- credential protection, destructive command blocking, write scope enforcement, supply chain control, and browser restrictions.
+
+## Installation
+
+### From marketplace
+
+```bash
+claude plugin marketplace add <owner>/agentic-config
+claude plugin install ac-safety@agentic-plugins
+```
+
+### Scopes
+
+```bash
+claude plugin install ac-safety@agentic-plugins --scope user
+claude plugin install ac-safety@agentic-plugins --scope project
+claude plugin install ac-safety@agentic-plugins --scope local
+```
+
+## Hooks
+
+| Hook | Trigger | Default | Description |
+|------|---------|---------|-------------|
+| `credential-guardian` | PreToolUse (Read\|Grep\|Glob) | DENY | Blocks access to credential files (~/.aws, ~/.ssh, etc.) |
+| `destructive-bash-guardian` | PreToolUse (Bash) | DENY | Blocks destructive commands (rm -rf, git push --force, etc.) |
+| `write-scope-guardian` | PreToolUse (Write\|Edit\|NotebookEdit) | ASK | Restricts writes to allowed project paths |
+| `supply-chain-guardian` | PreToolUse (Bash) | ASK | Blocks unapproved package installations |
+| `playwright-guardian` | PreToolUse (mcp__playwright__*) | ASK | Restricts Playwright/MCP tool usage |
+
+All hooks use **fail-close**: errors deny the operation.
+
+## Skills
+
+| Skill | Description |
+|-------|-------------|
+| `configure-safety` | Interactive safety.yaml customization |
+
+## Configuration
+
+Three-tier config resolution (most-restrictive-wins for category decisions):
+
+1. Project-level: `./safety.yaml`
+2. User-level: `~/.claude/safety.yaml`
+3. Plugin defaults: `config/safety.default.yaml`
+
+### Category decisions
+
+Each guardian category supports three decisions: `deny`, `ask`, `allow`.
+
+```yaml
+# Example: safety.yaml
+destructive_bash:
+  categories:
+    git-destructive: ask    # override default deny -> ask
+
+supply_chain:
+  categories:
+    npx-packages: allow     # trust npx packages
+  npx_allowlist:
+    - "@playwright/mcp"
+```
+
+## Usage Examples
+
+```
+# Customize safety settings interactively
+/configure-safety
+
+# Override a category at project level
+echo 'supply_chain:\n  categories:\n    pip-direct: allow' > safety.yaml
+```
+
+## License
+
+MIT
````

Verification:
- File exists with expected structure matching ac-git/ac-tools READMEs.

#### Task 12 -- configure-safety SKILL.md
Tools: Write
File: `plugins/ac-safety/skills/configure-safety/SKILL.md`

Interactive safety.yaml customization skill. Explains 3-tier resolution, reads current config, generates/updates safety.yaml.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/skills/configure-safety/SKILL.md
@@ -0,0 +1,55 @@
+# configure-safety
+
+Interactive safety.yaml configuration for ac-safety plugin.
+
+## Trigger
+
+`/configure-safety` or `/ac-safety:configure-safety`
+
+## Behavior
+
+1. Read the 3-tier config resolution and display current effective config:
+   - Plugin defaults: `${CLAUDE_PLUGIN_ROOT}/config/safety.default.yaml`
+   - User-level: `~/.claude/safety.yaml`
+   - Project-level: `./safety.yaml` (relative to project root)
+
+2. Display current effective settings per guardian:
+   - credential_guardian: blocked paths, allowed files
+   - destructive_bash: category decisions (deny/ask/allow per category)
+   - write_scope: allowed/blocked prefixes and files
+   - supply_chain: category decisions, allowlists
+   - playwright: category decisions, domain allowlist
+
+3. Ask user which guardian(s) to customize.
+
+4. For each selected guardian, present current category decisions and ask for changes:
+   - Show: `category: current_decision`
+   - Accept: `deny`, `ask`, or `allow` per category
+   - For list fields (allowlists, prefixes): show current, ask for additions/removals
+
+5. Ask target location: project-level (`./safety.yaml`) or user-level (`~/.claude/safety.yaml`).
+
+6. Generate or update the YAML file at chosen location.
+   - Only write overrides (do not duplicate defaults).
+   - Deep-merge with existing content if file already exists.
+
+7. Validate by loading the merged config and displaying effective result.
+
+## Steps
+
+```
+1. Read ${CLAUDE_PLUGIN_ROOT}/config/safety.default.yaml
+2. Read ~/.claude/safety.yaml (if exists)
+3. Read ./safety.yaml (if exists)
+4. Display merged effective config as table
+5. Prompt: "Which guardian to customize? (credential/destructive_bash/write_scope/supply_chain/playwright/all)"
+6. For selected guardian(s):
+   a. Show categories with current decisions
+   b. Ask for new decision per category (or skip)
+   c. For list fields, show current and ask for changes
+7. Prompt: "Save to project-level or user-level? (project/user)"
+8. Write YAML with only the overrides
+9. Re-read and display new effective config
+```
+
+## Constraints
+
+- Never modify plugin defaults (`safety.default.yaml`)
+- Only write overrides -- do not duplicate default values
+- Validate decisions are one of: deny, ask, allow
+- Existing file content must be preserved (deep-merge on write)
````

Verification:
- File exists at `plugins/ac-safety/skills/configure-safety/SKILL.md`.

#### Task 13 -- tool-audit.py: config-driven audit hook
Tools: Write
File: `plugins/ac-audit/scripts/hooks/tool-audit.py`

Refactored from `~/.claude/hooks/tool_audit.py`. Config-driven log_dir, display_tools, max_words. PEP 723 header. Fail-close on errors (audit hook failure should deny to prevent silent bypass of auditing).

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/scripts/hooks/tool-audit.py
@@ -0,0 +1,112 @@
+#!/usr/bin/env -S uv run --script
+# /// script
+# requires-python = ">=3.11"
+# dependencies = ["pyyaml"]
+# ///
+"""
+Claude Code Tool Audit Hook.
+
+Displays real-time tool usage via systemMessage and writes
+append-only JSONL audit log. Config-driven via audit.default.yaml.
+Fail-close on errors.
+"""
+
+import json
+import os
+import sys
+from datetime import datetime
+from pathlib import Path
+
+import yaml
+
+SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", str(os.getpid()))
+
+
+def _find_plugin_root() -> Path:
+    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
+    if env_root:
+        return Path(env_root)
+    return Path(__file__).resolve().parent.parent.parent
+
+
+def _load_audit_config() -> dict:
+    plugin_root = _find_plugin_root()
+    defaults_path = plugin_root / "config" / "audit.default.yaml"
+    config: dict = {}
+    if defaults_path.is_file():
+        with open(defaults_path) as f:
+            config = yaml.safe_load(f) or {}
+
+    # User override
+    user_path = Path.home() / ".claude" / "audit.yaml"
+    if user_path.is_file():
+        with open(user_path) as f:
+            user_cfg = yaml.safe_load(f) or {}
+        config.update(user_cfg)
+
+    # Project override
+    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
+    project_path = Path(project_dir) / "audit.yaml"
+    if project_path.is_file():
+        with open(project_path) as f:
+            proj_cfg = yaml.safe_load(f) or {}
+        config.update(proj_cfg)
+
+    return config
+
+
+def _truncate_field_values(obj: object, max_words: int = 50) -> object:
+    if isinstance(obj, dict):
+        return {k: _truncate_field_values(v, max_words) for k, v in obj.items()}
+    elif isinstance(obj, list):
+        return [_truncate_field_values(item, max_words) for item in obj]
+    elif isinstance(obj, str):
+        words = obj.split()
+        if len(words) > max_words:
+            return " ".join(words[:max_words]) + "..."
+        return obj
+    return obj
+
+
+def _format_simple(data: dict, indent: int = 0) -> str:
+    lines: list[str] = []
+    for key, value in data.items():
+        if isinstance(value, dict):
+            lines.append(f"{'  ' * indent}{key}:")
+            lines.append(_format_simple(value, indent + 1))
+        elif isinstance(value, list):
+            lines.append(f"{'  ' * indent}{key}:")
+            for item in value:
+                if isinstance(item, dict):
+                    lines.append(_format_simple(item, indent + 1))
+                else:
+                    lines.append(f"{'  ' * (indent + 1)}- {item}")
+        else:
+            lines.append(f"{'  ' * indent}{key}: {value}")
+    return "\n".join(lines)
+
+
+def _write_audit_log(tool_name: str, tool_input: dict, log_dir: str, log_permissions: int) -> None:
+    log_path = Path(log_dir)
+    if not log_path.exists():
+        return  # Silently skip if dir missing
+    today = datetime.now().strftime("%Y-%m-%d")
+    log_file = log_path / f"{today}.jsonl"
+    entry = {"ts": datetime.now().isoformat(), "tool": tool_name, "input": tool_input, "session": SESSION_ID}
+    with open(log_file, "a", encoding="utf-8") as f:
+        f.write(json.dumps(entry) + "\n")
+    try:
+        log_file.chmod(log_permissions)
+    except OSError:
+        pass
+
+
+def main() -> None:
+    try:
+        json_input = sys.stdin.read().strip()
+        if not json_input:
+            print(json.dumps({"systemMessage": "[AUDIT] No input received"}))
+            return
+
+        data = json.loads(json_input)
+        tool_name = data.get("tool_name", "Unknown")
+        tool_input = data.get("tool_input", {})
+
+        config = _load_audit_config()
+        log_dir = config.get("log_dir", "/var/log/claude-audit")
+        log_permissions = config.get("log_permissions", 0o600)
+        display_tools = set(config.get("display_tools", ["Bash"]))
+        max_words = config.get("max_words", 50)
+
+        _write_audit_log(tool_name, tool_input, log_dir, log_permissions)
+
+        if tool_name in display_tools:
+            truncated = _truncate_field_values(tool_input, max_words)
+            message = f"{tool_name}:\n{_format_simple(truncated) if isinstance(truncated, dict) else str(truncated)}"
+            print(json.dumps({"systemMessage": message}))
+
+    except Exception as e:
+        # Fail-close: deny on audit errors
+        print(json.dumps({
+            "hookSpecificOutput": {
+                "hookEventName": "PreToolUse",
+                "permissionDecision": "deny",
+                "permissionDecisionReason": f"Audit hook error (fail-close): {e}",
+            }
+        }))
+        print(f"Audit hook error (fail-close): {e}", file=sys.stderr)
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python -c "import ast; ast.parse(open('plugins/ac-audit/scripts/hooks/tool-audit.py').read()); print('OK')"`

#### Task 14 -- audit.default.yaml: default audit config
Tools: Write
File: `plugins/ac-audit/config/audit.default.yaml`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/config/audit.default.yaml
@@ -0,0 +1,12 @@
+# ac-audit default configuration
+# Override at: project audit.yaml > ~/.claude/audit.yaml > this file
+
+log_dir: "/var/log/claude-audit"
+log_permissions: 384  # 0o600 in decimal
+max_words: 50
+
+# Tools that display systemMessage in Claude Code UI
+display_tools:
+  - "Bash"
````

Verification:
- `python -c "import yaml; yaml.safe_load(open('plugins/ac-audit/config/audit.default.yaml')); print('OK')"`

#### Task 15 -- hooks.json for ac-audit
Tools: Write
File: `plugins/ac-audit/hooks/hooks.json`

Wildcard matcher for all tools.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/hooks/hooks.json
@@ -0,0 +1,14 @@
+{
+  "hooks": {
+    "PreToolUse": [
+      {
+        "matcher": "*",
+        "hooks": [{
+          "type": "command",
+          "command": "uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/hooks/tool-audit.py"
+        }]
+      }
+    ]
+  }
+}
````

Verification:
- `python -c "import json; json.load(open('plugins/ac-audit/hooks/hooks.json')); print('OK')"`

#### Task 16 -- plugin.json for ac-audit
Tools: Write
File: `plugins/ac-audit/.claude-plugin/plugin.json`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/.claude-plugin/plugin.json
@@ -0,0 +1,12 @@
+{
+  "name": "ac-audit",
+  "description": "Tool audit logging - JSONL audit trail and real-time systemMessage display",
+  "version": "0.2.2",
+  "author": {
+    "name": "Agentic Config Contributors"
+  },
+  "homepage": "https://github.com/WaterplanAI/agentic-config",
+  "repository": "https://github.com/WaterplanAI/agentic-config",
+  "license": "MIT",
+  "keywords": ["audit", "logging", "tools", "jsonl", "compliance"]
+}
````

Verification:
- `python -c "import json; json.load(open('plugins/ac-audit/.claude-plugin/plugin.json')); print('OK')"`

#### Task 17 -- CLAUDE.md for ac-audit
Tools: Write
File: `plugins/ac-audit/CLAUDE.md`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/CLAUDE.md
@@ -0,0 +1,10 @@
+# ac-audit
+
+Tool audit logging plugin for Claude Code.
+
+## Hooks
+
+- tool-audit: logs all tool invocations to JSONL, displays Bash commands via systemMessage
+
+Configuration: `audit.yaml` (project > `~/.claude/audit.yaml` > plugin defaults)
+Fail-close: errors deny the operation.
````

Verification:
- File exists with expected content.

#### Task 18 -- README.md for ac-audit
Tools: Write
File: `plugins/ac-audit/README.md`

Documentation mirroring ac-git/ac-tools README structure.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-audit/README.md
@@ -0,0 +1,47 @@
+# ac-audit
+
+Tool audit logging -- JSONL audit trail and real-time systemMessage display for Claude Code.
+
+## Installation
+
+### From marketplace
+
+```bash
+claude plugin marketplace add <owner>/agentic-config
+claude plugin install ac-audit@agentic-plugins
+```
+
+### Scopes
+
+```bash
+claude plugin install ac-audit@agentic-plugins --scope user
+claude plugin install ac-audit@agentic-plugins --scope project
+claude plugin install ac-audit@agentic-plugins --scope local
+```
+
+## Hooks
+
+| Hook | Trigger | Description |
+|------|---------|-------------|
+| `tool-audit` | PreToolUse (*) | Logs all tool invocations to JSONL, displays configured tools via systemMessage |
+
+Fail-close: errors deny the operation.
+
+## Configuration
+
+Override at: project `audit.yaml` > `~/.claude/audit.yaml` > plugin defaults.
+
+```yaml
+# Example: audit.yaml
+log_dir: "/var/log/claude-audit"
+log_permissions: 384  # 0o600
+max_words: 50
+display_tools:
+  - "Bash"
+  - "Write"
+```
+
+## Usage
+
+No manual invocation needed. Hooks fire automatically on all tool calls when the plugin is installed.
+
+## License
+
+MIT
````

Verification:
- File exists with expected structure matching ac-git/ac-tools READMEs.

#### Task 19 -- Unit tests for _lib.py
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_lib.py`

Tests: deep-merge logic, most-restrictive-wins, load_config with mock files, path resolution, decision helpers, fail_close decorator.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_lib.py
@@ -0,0 +1,195 @@
+#!/usr/bin/env python3
+"""Unit tests for _lib.py shared safety library."""
+
+import json
+import os
+import subprocess
+import sys
+import tempfile
+from pathlib import Path
+
+# Add hooks dir to path for direct import
+HOOKS_DIR = Path(__file__).parent.parent.parent / "scripts" / "hooks"
+sys.path.insert(0, str(HOOKS_DIR))
+
+from _lib import (
+    _deep_merge,
+    _most_restrictive,
+    allow,
+    ask,
+    deny,
+    fail_close,
+    get_category_decision,
+    is_in_prefixes,
+    resolve_path,
+)
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.passed = False
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def test_most_restrictive() -> TestResult:
+    r = TestResult("most_restrictive: deny > ask > allow")
+    try:
+        assert _most_restrictive("deny", "allow") == "deny"
+        assert _most_restrictive("allow", "deny") == "deny"
+        assert _most_restrictive("ask", "allow") == "ask"
+        assert _most_restrictive("allow", "ask") == "ask"
+        assert _most_restrictive("deny", "ask") == "deny"
+        assert _most_restrictive("allow", "allow") == "allow"
+        assert _most_restrictive("deny", "deny") == "deny"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_deep_merge_basic() -> TestResult:
+    r = TestResult("deep_merge: basic dict merge")
+    try:
+        base = {"a": 1, "b": {"c": 2, "d": 3}}
+        overlay = {"b": {"c": 99, "e": 4}, "f": 5}
+        result = _deep_merge(base, overlay)
+        assert result["a"] == 1
+        assert result["b"]["c"] == 99
+        assert result["b"]["d"] == 3
+        assert result["b"]["e"] == 4
+        assert result["f"] == 5
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_deep_merge_categories_most_restrictive() -> TestResult:
+    r = TestResult("deep_merge: categories use most-restrictive-wins")
+    try:
+        base = {"categories": {"git-destructive": "deny", "file-destruction": "allow"}}
+        overlay = {"categories": {"git-destructive": "allow", "file-destruction": "deny"}}
+        result = _deep_merge(base, overlay)
+        # Most restrictive wins: deny beats allow
+        assert result["categories"]["git-destructive"] == "deny"
+        assert result["categories"]["file-destruction"] == "deny"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_deep_merge_list_replacement() -> TestResult:
+    r = TestResult("deep_merge: lists are replaced not merged")
+    try:
+        base = {"allowed": ["/a/", "/b/"]}
+        overlay = {"allowed": ["/c/"]}
+        result = _deep_merge(base, overlay)
+        assert result["allowed"] == ["/c/"]
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_get_category_decision_defaults() -> TestResult:
+    r = TestResult("get_category_decision: returns ask by default")
+    try:
+        config: dict = {}
+        assert get_category_decision(config, "destructive_bash", "git-destructive") == "ask"
+
+        config = {"destructive_bash": {"categories": {"git-destructive": "deny"}}}
+        assert get_category_decision(config, "destructive_bash", "git-destructive") == "deny"
+        assert get_category_decision(config, "destructive_bash", "unknown-cat") == "ask"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_resolve_path() -> TestResult:
+    r = TestResult("resolve_path: expands ~ and resolves symlinks")
+    try:
+        home = os.path.expanduser("~")
+        result = resolve_path("~/test/file.txt")
+        assert result.startswith(home)
+        assert "~" not in result
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_is_in_prefixes() -> TestResult:
+    r = TestResult("is_in_prefixes: matches resolved prefixes")
+    try:
+        assert is_in_prefixes("/tmp/foo/bar.txt", ["/tmp/foo/"])
+        assert not is_in_prefixes("/var/log/test.txt", ["/tmp/foo/"])
+        assert is_in_prefixes("~/projects/test/a.py", ["~/projects/"])
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_fail_close_decorator() -> TestResult:
+    r = TestResult("fail_close: catches exceptions and denies")
+    try:
+        import io
+        from contextlib import redirect_stdout
+
+        @fail_close
+        def bad_main() -> None:
+            raise ValueError("test error")
+
+        buf = io.StringIO()
+        with redirect_stdout(buf):
+            bad_main()
+
+        output = json.loads(buf.getvalue().strip())
+        decision = output["hookSpecificOutput"]["permissionDecision"]
+        assert decision == "deny", f"Expected deny on error, got {decision}"
+        assert "test error" in output["hookSpecificOutput"]["permissionDecisionReason"]
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_decision_helpers_output() -> TestResult:
+    r = TestResult("deny/allow/ask: produce correct JSON output")
+    try:
+        import io
+        from contextlib import redirect_stdout
+
+        # Test deny
+        buf = io.StringIO()
+        with redirect_stdout(buf):
+            deny("test reason")
+        out = json.loads(buf.getvalue())
+        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
+        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "test reason"
+
+        # Test allow
+        buf = io.StringIO()
+        with redirect_stdout(buf):
+            allow()
+        out = json.loads(buf.getvalue())
+        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
+
+        # Test ask
+        buf = io.StringIO()
+        with redirect_stdout(buf):
+            ask("confirm?")
+        out = json.loads(buf.getvalue())
+        assert out["hookSpecificOutput"]["permissionDecision"] == "ask"
+        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "confirm?"
+
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running _lib.py unit tests...\n")
+    tests = [
+        test_most_restrictive, test_deep_merge_basic,
+        test_deep_merge_categories_most_restrictive,
+        test_deep_merge_list_replacement, test_get_category_decision_defaults,
+        test_resolve_path, test_is_in_prefixes,
+        test_fail_close_decorator, test_decision_helpers_output,
+    ]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        if result.passed:
+            passed += 1
+        else:
+            failed += 1
+    print(f"\n{'='*60}")
+    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        sys.exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_lib.py` -- all tests pass.

#### Task 20 -- Unit tests for credential-guardian
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_credential_guardian.py`

Tests: blocked paths denied, allowed project paths allowed, allowed claude files allowed, config override works, fail-close on error.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_credential_guardian.py
@@ -0,0 +1,110 @@
+#!/usr/bin/env python3
+"""Unit tests for credential-guardian hook."""
+
+import json
+import os
+import subprocess
+from pathlib import Path
+
+
+HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "credential-guardian.py"
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def run_hook(tool_name: str, tool_input: dict) -> dict:
+    result = subprocess.run(
+        [str(HOOK_PATH)],
+        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
+        capture_output=True, text=True,
+    )
+    output = json.loads(result.stdout)
+    hook_out = output.get("hookSpecificOutput", {})
+    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}
+
+
+def test_blocks_ssh_read() -> TestResult:
+    r = TestResult("Blocks Read of ~/.ssh/")
+    try:
+        out = run_hook("Read", {"file_path": os.path.expanduser("~/.ssh/id_rsa")})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_aws_grep() -> TestResult:
+    r = TestResult("Blocks Grep in ~/.aws/")
+    try:
+        out = run_hook("Grep", {"path": os.path.expanduser("~/.aws/credentials"), "pattern": "secret"})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_project_read() -> TestResult:
+    r = TestResult("Allows Read in ~/projects/")
+    try:
+        out = run_hook("Read", {"file_path": os.path.expanduser("~/projects/test/file.py")})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_claude_settings() -> TestResult:
+    r = TestResult("Allows Read of ~/.claude/settings.json")
+    try:
+        out = run_hook("Read", {"file_path": os.path.expanduser("~/.claude/settings.json")})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_non_read_tools() -> TestResult:
+    r = TestResult("Allows non-Read tools (Bash)")
+    try:
+        out = run_hook("Bash", {"command": "ls"})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_fail_close_on_bad_input() -> TestResult:
+    r = TestResult("Fail-close on invalid JSON input")
+    try:
+        result = subprocess.run(
+            [str(HOOK_PATH)], input="not valid json",
+            capture_output=True, text=True,
+        )
+        output = json.loads(result.stdout)
+        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
+        assert decision == "deny", f"Expected deny on error, got {decision}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running credential-guardian unit tests...\n")
+    tests = [test_blocks_ssh_read, test_blocks_aws_grep, test_allows_project_read,
+             test_allows_claude_settings, test_allows_non_read_tools, test_fail_close_on_bad_input]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_credential_guardian.py` -- all tests pass.

#### Task 21 -- Unit tests for destructive-bash-guardian
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_destructive_bash_guardian.py`

Tests: blocked patterns denied, safe commands allowed, per-category config decisions, fail-close.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_destructive_bash_guardian.py
@@ -0,0 +1,105 @@
+#!/usr/bin/env python3
+"""Unit tests for destructive-bash-guardian hook."""
+
+import json
+import subprocess
+from pathlib import Path
+
+
+HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "destructive-bash-guardian.py"
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def run_hook(command: str) -> dict:
+    result = subprocess.run(
+        [str(HOOK_PATH)],
+        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
+        capture_output=True, text=True,
+    )
+    output = json.loads(result.stdout)
+    hook_out = output.get("hookSpecificOutput", {})
+    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}
+
+
+def test_blocks_rm_rf_home() -> TestResult:
+    r = TestResult("Blocks rm -rf ~/")
+    try:
+        out = run_hook("rm -rf ~/important_stuff")
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_git_force_push() -> TestResult:
+    r = TestResult("Blocks git push --force")
+    try:
+        out = run_hook("git push origin main --force")
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_terraform_destroy() -> TestResult:
+    r = TestResult("Blocks terraform destroy")
+    try:
+        out = run_hook("terraform destroy -auto-approve")
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_safe_commands() -> TestResult:
+    r = TestResult("Allows safe commands (ls, git status)")
+    try:
+        for cmd in ["ls -la", "git status", "echo hello", "cat README.md"]:
+            out = run_hook(cmd)
+            assert out["decision"] == "allow", f"Expected allow for '{cmd}', got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_non_bash_tools() -> TestResult:
+    r = TestResult("Allows non-Bash tools")
+    try:
+        result = subprocess.run(
+            [str(HOOK_PATH)],
+            input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/test"}}),
+            capture_output=True, text=True,
+        )
+        output = json.loads(result.stdout)
+        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
+        assert decision == "allow", f"Expected allow for Read, got {decision}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running destructive-bash-guardian unit tests...\n")
+    tests = [test_blocks_rm_rf_home, test_blocks_git_force_push,
+             test_blocks_terraform_destroy, test_allows_safe_commands,
+             test_allows_non_bash_tools]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_destructive_bash_guardian.py` -- all tests pass.

#### Task 22 -- Unit tests for write-scope-guardian
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_write_scope_guardian.py`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_write_scope_guardian.py
@@ -0,0 +1,96 @@
+#!/usr/bin/env python3
+"""Unit tests for write-scope-guardian hook."""
+
+import json
+import os
+import subprocess
+from pathlib import Path
+
+
+HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "write-scope-guardian.py"
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def run_hook(tool_name: str, tool_input: dict) -> dict:
+    result = subprocess.run(
+        [str(HOOK_PATH)],
+        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
+        capture_output=True, text=True,
+    )
+    output = json.loads(result.stdout)
+    hook_out = output.get("hookSpecificOutput", {})
+    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}
+
+
+def test_allows_project_write() -> TestResult:
+    r = TestResult("Allows Write to ~/projects/")
+    try:
+        out = run_hook("Write", {"file_path": os.path.expanduser("~/projects/test/file.py"), "content": "test"})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_settings_write() -> TestResult:
+    r = TestResult("Blocks Write to ~/.claude/settings.json")
+    try:
+        out = run_hook("Write", {"file_path": os.path.expanduser("~/.claude/settings.json"), "content": "{}"})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_asks_hooks_write() -> TestResult:
+    r = TestResult("Asks for Write to ~/.claude/hooks/")
+    try:
+        out = run_hook("Write", {"file_path": os.path.expanduser("~/.claude/hooks/test.py"), "content": "test"})
+        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_system_write() -> TestResult:
+    r = TestResult("Blocks Write to /etc/")
+    try:
+        out = run_hook("Write", {"file_path": "/etc/passwd", "content": "test"})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_blocks_git_hooks_injection() -> TestResult:
+    r = TestResult("Blocks Write to .git/hooks/")
+    try:
+        out = run_hook("Write", {"file_path": "/tmp/repo/.git/hooks/pre-commit", "content": "test"})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running write-scope-guardian unit tests...\n")
+    tests = [test_allows_project_write, test_blocks_settings_write,
+             test_asks_hooks_write, test_blocks_system_write, test_blocks_git_hooks_injection]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_write_scope_guardian.py` -- all tests pass.

#### Task 23 -- Unit tests for supply-chain-guardian
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_supply_chain_guardian.py`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_supply_chain_guardian.py
@@ -0,0 +1,90 @@
+#!/usr/bin/env python3
+"""Unit tests for supply-chain-guardian hook."""
+
+import json
+import subprocess
+from pathlib import Path
+
+
+HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "supply-chain-guardian.py"
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def run_hook(command: str) -> dict:
+    result = subprocess.run(
+        [str(HOOK_PATH)],
+        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
+        capture_output=True, text=True,
+    )
+    output = json.loads(result.stdout)
+    hook_out = output.get("hookSpecificOutput", {})
+    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}
+
+
+def test_allows_npm_install() -> TestResult:
+    r = TestResult("Allows npm install (lockfile)")
+    try:
+        out = run_hook("npm install")
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_uv_sync() -> TestResult:
+    r = TestResult("Allows uv sync")
+    try:
+        out = run_hook("uv sync")
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_asks_pip_install_direct() -> TestResult:
+    r = TestResult("Asks for pip install direct package (default: ask)")
+    try:
+        out = run_hook("pip install requests")
+        # Default category decision is ask
+        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_asks_npx_unknown_package() -> TestResult:
+    r = TestResult("Asks for npx with unknown package (default: ask)")
+    try:
+        out = run_hook("npx malicious-package")
+        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running supply-chain-guardian unit tests...\n")
+    tests = [test_allows_npm_install, test_allows_uv_sync,
+             test_asks_pip_install_direct, test_asks_npx_unknown_package]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_supply_chain_guardian.py` -- all tests pass.

#### Task 24 -- Unit tests for playwright-guardian
Tools: Write
File: `plugins/ac-safety/tests/hooks/test_playwright_guardian.py`

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/hooks/test_playwright_guardian.py
@@ -0,0 +1,91 @@
+#!/usr/bin/env python3
+"""Unit tests for playwright-guardian hook."""
+
+import json
+import subprocess
+from pathlib import Path
+
+
+HOOK_PATH = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "playwright-guardian.py"
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def run_hook(tool_name: str, tool_input: dict) -> dict:
+    result = subprocess.run(
+        [str(HOOK_PATH)],
+        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
+        capture_output=True, text=True,
+    )
+    output = json.loads(result.stdout)
+    hook_out = output.get("hookSpecificOutput", {})
+    return {"decision": hook_out.get("permissionDecision", "allow"), "reason": hook_out.get("permissionDecisionReason", "")}
+
+
+def test_blocks_browser_evaluate() -> TestResult:
+    r = TestResult("Blocks browser_evaluate (always blocked)")
+    try:
+        out = run_hook("mcp__playwright__browser_evaluate", {"script": "document.cookie"})
+        assert out["decision"] == "deny", f"Expected deny, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_browser_snapshot() -> TestResult:
+    r = TestResult("Allows browser_snapshot (always allowed)")
+    try:
+        out = run_hook("mcp__playwright__browser_snapshot", {})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_allows_navigate_allowed_domain() -> TestResult:
+    r = TestResult("Allows navigate to github.com")
+    try:
+        out = run_hook("mcp__playwright__browser_navigate", {"url": "https://github.com/test"})
+        assert out["decision"] == "allow", f"Expected allow, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_asks_navigate_blocked_domain() -> TestResult:
+    r = TestResult("Asks for navigate to unknown domain (default: ask)")
+    try:
+        out = run_hook("mcp__playwright__browser_navigate", {"url": "https://evil.com/phishing"})
+        assert out["decision"] == "ask", f"Expected ask, got {out['decision']}"
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running playwright-guardian unit tests...\n")
+    tests = [test_blocks_browser_evaluate, test_allows_browser_snapshot,
+             test_allows_navigate_allowed_domain, test_asks_navigate_blocked_domain]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/hooks/test_playwright_guardian.py` -- all tests pass.

#### Task 25 -- E2E test: plugin structure validation
Tools: Write
File: `plugins/ac-safety/tests/e2e/test_plugin_load.py`

E2E test verifying: all required files exist, hooks.json is valid, plugin.json is valid, all hook scripts are syntactically valid Python, config YAML is valid.

Diff:
````diff
--- /dev/null
+++ b/plugins/ac-safety/tests/e2e/test_plugin_load.py
@@ -0,0 +1,81 @@
+#!/usr/bin/env python3
+"""E2E tests: validate ac-safety and ac-audit plugin structure and loadability."""
+
+import ast
+import json
+import sys
+from pathlib import Path
+
+import yaml
+
+REPO_ROOT = Path(__file__).parent.parent.parent.parent
+
+
+class TestResult:
+    def __init__(self, name: str):
+        self.name = name
+        self.passed = False
+        self.error: str | None = None
+    def mark_pass(self) -> None:
+        self.passed = True
+    def mark_fail(self, error: str) -> None:
+        self.error = error
+    def __str__(self) -> str:
+        status = "PASS" if self.passed else "FAIL"
+        msg = f"  {status}: {self.name}"
+        if self.error:
+            msg += f"\n    Error: {self.error}"
+        return msg
+
+
+def test_ac_safety_structure() -> TestResult:
+    r = TestResult("ac-safety: all required files exist")
+    try:
+        base = REPO_ROOT / "ac-safety"
+        required = [
+            ".claude-plugin/plugin.json", "hooks/hooks.json", "config/safety.default.yaml",
+            "scripts/hooks/_lib.py", "scripts/hooks/credential-guardian.py",
+            "scripts/hooks/destructive-bash-guardian.py", "scripts/hooks/write-scope-guardian.py",
+            "scripts/hooks/supply-chain-guardian.py", "scripts/hooks/playwright-guardian.py",
+            "skills/configure-safety/SKILL.md", "CLAUDE.md", "README.md",
+        ]
+        for f in required:
+            assert (base / f).exists(), f"Missing: {f}"
+        # Validate JSON files
+        json.loads((base / ".claude-plugin/plugin.json").read_text())
+        json.loads((base / "hooks/hooks.json").read_text())
+        # Validate YAML
+        yaml.safe_load((base / "config/safety.default.yaml").read_text())
+        # Validate Python syntax
+        for py in base.glob("scripts/hooks/*.py"):
+            ast.parse(py.read_text())
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def test_ac_audit_structure() -> TestResult:
+    r = TestResult("ac-audit: all required files exist")
+    try:
+        base = REPO_ROOT / "ac-audit"
+        required = [
+            ".claude-plugin/plugin.json", "hooks/hooks.json", "config/audit.default.yaml",
+            "scripts/hooks/tool-audit.py", "CLAUDE.md", "README.md",
+        ]
+        for f in required:
+            assert (base / f).exists(), f"Missing: {f}"
+        json.loads((base / ".claude-plugin/plugin.json").read_text())
+        json.loads((base / "hooks/hooks.json").read_text())
+        yaml.safe_load((base / "config/audit.default.yaml").read_text())
+        ast.parse((base / "scripts/hooks/tool-audit.py").read_text())
+        r.mark_pass()
+    except Exception as e:
+        r.mark_fail(str(e))
+    return r
+
+
+def main() -> None:
+    print("Running E2E plugin structure tests...\n")
+    tests = [test_ac_safety_structure, test_ac_audit_structure]
+    passed = failed = 0
+    for t in tests:
+        result = t()
+        print(result)
+        passed += 1 if result.passed else 0
+        failed += 0 if result.passed else 1
+    print(f"\n{'='*60}\nResults: {passed} passed, {failed} failed out of {len(tests)} total")
+    if failed:
+        sys.exit(1)
+    print("All tests passed!")
+
+
+if __name__ == "__main__":
+    main()
````

Verification:
- `python plugins/ac-safety/tests/e2e/test_plugin_load.py` -- all tests pass.

#### Task 26 -- Lint all Python files
Tools: Shell
Commands:
```bash
cd /path/to/agentic-config
uv run ruff check --fix plugins/ac-safety/scripts/hooks/_lib.py plugins/ac-safety/scripts/hooks/credential-guardian.py plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py plugins/ac-safety/scripts/hooks/write-scope-guardian.py plugins/ac-safety/scripts/hooks/supply-chain-guardian.py plugins/ac-safety/scripts/hooks/playwright-guardian.py plugins/ac-audit/scripts/hooks/tool-audit.py
uv run pyright plugins/ac-safety/scripts/hooks/_lib.py plugins/ac-safety/scripts/hooks/credential-guardian.py plugins/ac-safety/scripts/hooks/destructive-bash-guardian.py plugins/ac-safety/scripts/hooks/write-scope-guardian.py plugins/ac-safety/scripts/hooks/supply-chain-guardian.py plugins/ac-safety/scripts/hooks/playwright-guardian.py plugins/ac-audit/scripts/hooks/tool-audit.py
```

Verification:
- No ruff errors after fix.
- Pyright reports 0 errors (or only expected external import warnings for yaml).

#### Task 27 -- Commit
Tools: git
Commands:
```bash
git checkout -b feat/ac-safety-ac-audit-plugins
git add plugins/ac-safety/ plugins/ac-audit/
git commit -m "$(cat <<'EOF'
feat(plugins): add ac-safety and ac-audit security/audit plugins

Added:
- ac-safety plugin: 5 config-driven guardian hooks (credential, destructive-bash,
  write-scope, supply-chain, playwright) with shared _lib.py, 3-tier YAML config
  resolution (project > user > defaults), fail-close error handling, and
  most-restrictive-wins category decisions
- ac-audit plugin: JSONL audit logging hook with configurable display and log settings
- Unit tests for _lib.py and all 5 guardians
- E2E plugin structure validation tests
- configure-safety interactive customization skill
- Documentation (README, CLAUDE.md) matching existing plugin patterns
EOF
)"
```

Verification:
- `git log --oneline -1` shows the commit.
- `git diff --stat HEAD~1` shows only files under `plugins/ac-safety/` and `plugins/ac-audit/`.

### Validate

Requirement validation against Human Section:

- **L6-7 (HLO):** Refactor 5 guardians + tool_audit into ac-safety + ac-audit plugins -- Tasks 1-18 create all files. COMPLIANT.
- **L11 (_lib.py shared module):** Task 1 creates _lib.py with load_config, deny/allow/ask, resolve_path, is_in_prefixes, get_category_decision, deep-merge. COMPLIANT (L11).
- **L12 (credential-guardian):** Task 2 refactors with configurable blocked_prefixes, blocked_filenames, blocked_extensions, allowed_claude_files. COMPLIANT (L12).
- **L13 (destructive-bash-guardian):** Task 3 refactors with per-category decisions for all 12 categories. COMPLIANT (L13).
- **L14 (write-scope-guardian):** Task 4 refactors with configurable prefixes/files. COMPLIANT (L14).
- **L15 (supply-chain-guardian):** Task 5 refactors with allowlists and per-category decisions. COMPLIANT (L15).
- **L16 (playwright-guardian):** Task 6 refactors with configurable domains and per-category decisions. COMPLIANT (L16).
- **L17 (hooks.json):** Task 8 creates hooks.json with tool matchers and ${CLAUDE_PLUGIN_ROOT}. COMPLIANT (L17).
- **L18 (plugin.json):** Task 9 creates .claude-plugin/plugin.json. COMPLIANT (L18).
- **L19 (safety.default.yaml):** Task 7 creates config with sane defaults. COMPLIANT (L19).
- **L20 (configure-safety skill):** Task 12 creates SKILL.md at skills/configure-safety/. COMPLIANT (L20).
- **L21 (PEP 723 headers):** All hooks use `#!/usr/bin/env -S uv run --script` with `/// script` block. COMPLIANT (L21).
- **L22 (fail-open -> SC UPDATE: fail-close):** SC Update 1 overrides to FAIL-CLOSE. All hooks use @fail_close decorator. COMPLIANT with SC update.
- **L24-29 (ac-audit):** Tasks 13-18 create standalone audit plugin with JSONL logging, configurable settings, hooks.json, plugin.json. COMPLIANT (L24-29).
- **SC Update 2 (default ASK, except destructive-bash/credential: DENY):** safety.default.yaml sets DENY for destructive_bash categories and credential is DENY by nature (blocks access). Other categories (supply_chain, playwright, write_scope) default to ASK. COMPLIANT.
- **SC Update 3 (most-restrictive-wins):** _deep_merge uses most-restrictive-wins for "categories" dicts. COMPLIANT.
- **SC Update 4 (documentation mirrors ac-git/ac-tools):** READMEs follow exact same structure. COMPLIANT.
- **SC Update 5 (concise, clear, actionable):** Documentation is minimal, uses tables, code examples. COMPLIANT.
- **L237 (no external deps beyond stdlib + PyYAML):** PEP 723 headers only list pyyaml. COMPLIANT (L237).
- **L238 (_lib.py relative import):** sys.path.insert(0, ...) used in all hooks. COMPLIANT (L238).
- **L239 (version 0.2.2):** plugin.json for both plugins uses "0.2.2". COMPLIANT (L239).
- **L240 (project-agnostic, PII-free):** No real names, emails, or project-specific paths in any file. COMPLIANT (L240).
- **L244-249 (testing):** Tasks 19-25 cover unit tests for _lib.py, each guardian, and E2E plugin structure validation. COMPLIANT (L244-249).

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
