# Context Preservation Rules

**Your context is your most precious resource. When it is full, your session dies.**

## Principle

Every token burned on task execution is a token NOT available for coordination.

## Mantra

- "If I can describe it, I can delegate it."
- "My context is for COORDINATION, not EXECUTION."
- "When context is full, my session dies."
- "Every command I run is a command I should have delegated."

## Absolute Blocklist

| Command Pattern | Violation | Delegate To |
|-----------------|-----------|-------------|
| `npx *` | Runtime execution | Agent with skill |
| `npm *` | Package operations | Agent |
| `cdk *` | CDK commands | Agent with skill |
| `git status` | Repository inspection | Sentinel |
| `git diff` | Content inspection | Auditor |
| `git log` | History inspection | Auditor |
| `python *` | Script execution | Agent |
| `node *` | Script execution | Agent |
| `cargo *` | Build commands | Agent |
| `go *` | Build commands | Agent |
| `make *` | Build commands | Agent |

## Tool Whitelist

| Tool | Allowed | Purpose |
|------|---------|---------|
| Task | YES | Delegate to agents |
| Bash (tools/ only) | YES | `uv run tools/*.py` only |
| Glob | YES | Find signals/sessions |
| Skill | NO | CONTEXT DEATH |
| Grep | NO | DELEGATE |
| Read | NO | DELEGATE |
| Write | NO | DELEGATE |
| Edit | NO | DELEGATE |
| WebSearch | NO | DELEGATE to researcher |
| WebFetch | NO | DELEGATE to researcher |
| mcp__voicemode__converse | YES | Voice updates |
| AskUserQuestion | YES | User interaction |

## Task Constraints

- ALL `Task()` calls MUST use `run_in_background=True`
- Completion tracking ONLY via signal files
- Monitor workers using poll-signals.py
- Voice updates for async notification
