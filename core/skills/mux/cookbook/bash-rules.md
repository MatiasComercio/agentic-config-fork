# Bash Restrictions

Orchestrator Bash usage is LIMITED to these EXACT tools.

## Allowed Commands

| Command | Purpose |
|---------|---------|
| `uv run tools/session.py` | Create session directory |
| `uv run tools/verify.py` | Check signal counts/status |
| `uv run tools/signal.py` | Create signals (emergency) |
| `uv run tools/poll-signals.py` | Monitor agent uses this |
| `uv run tools/agents.py` | List/register agents |
| `mkdir -p` | Create directories |
| `ls` | List directories only |

## Explicit Blocklist (FATAL)

| Command | Violation |
|---------|-----------|
| `npx *` | Runtime execution |
| `npm *` | Package operations |
| `cdk *` | CDK commands |
| `git status` | Repository inspection |
| `git diff` | Content inspection |
| `git log` | History inspection |
| `git show` | Commit inspection |
| `grep` / `rg` | Content search |
| `find` | File search |
| `cat` / `head` / `tail` | File reading |
| `python *` | Script execution |
| `node *` | Script execution |
| `cargo *` / `go *` | Build commands |
| `make` / `gradle` / `mvn` | Build commands |

## Evidence of Violations (Real Examples)

```bash
# FATAL - orchestrator ran CDK directly
npx cdk synth SdcStack

# FATAL - orchestrator inspected git
git status --porcelain | head -30

# FATAL - orchestrator ran grep
grep -rn "pattern" --include="*.md"
```

## Correct Delegation

```python
# CDK validation -> agent with skill
Task(prompt="Invoke /build-validate skill.", model="sonnet", run_in_background=True)

# Git inspection -> sentinel
Task(prompt="Read agents/sentinel.md. Check git status.", model="sonnet", run_in_background=True)

# Pattern search -> auditor
Task(prompt="Read agents/auditor.md. Search for pattern.", model="sonnet", run_in_background=True)
```

## Rationale

- Every bash command beyond tools/ pollutes context
- "Quick checks" become habit, eroding discipline
- If it's worth checking, it's worth delegating
- **When context is full, your session dies**
