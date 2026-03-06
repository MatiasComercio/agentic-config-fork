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
<!-- Filled by /spec PLAN -->

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
