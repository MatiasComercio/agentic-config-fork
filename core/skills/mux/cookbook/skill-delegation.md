# Skill Delegation

**NEVER invoke Skill() directly from orchestrator. ALWAYS delegate via Task().**

## Why

| Tool | Execution Context | Impact |
|------|-------------------|--------|
| `Skill()` | CURRENT agent (orchestrator) | Context DESTROYED |
| `Task()` | NEW subagent context | Context PRESERVED |

Skill() executes IN the calling agent's context. Running `/spec PLAN` in orchestrator = orchestrator death.

## Routing Table

| Pattern | WRONG (Context Suicide) | RIGHT (Context Preserved) |
|---------|-------------------------|---------------------------|
| `/spec PLAN` | `Skill(skill="spec", args="PLAN ...")` | `Task(prompt="Invoke Skill(skill='spec', args='PLAN ...')")` |
| `/spec IMPLEMENT` | `Skill(skill="spec", args="IMPLEMENT ...")` | `Task(prompt="Invoke Skill(skill='spec', args='IMPLEMENT ...')")` |
| `/commit` | `Skill(skill="commit")` | `Task(prompt="Invoke Skill(skill='commit')")` |
| `/review-pr` | `Skill(skill="review-pr", ...)` | `Task(prompt="Invoke Skill(skill='review-pr', ...)")` |
| Any skill | Direct `Skill()` call | `Task()` instructing subagent |

## Delegation Template

```python
Task(
    prompt="""Invoke the /spec skill for Phase 1 PLAN.

Use: Skill(skill="spec", args="PLAN 002-phase-001 THINK HARD")

OUTPUT: {output_path}
SIGNAL: {signal_path}
Return exactly: done""",
    subagent_type="general-purpose",
    model="opus",
    run_in_background=True
)
```

## Fatal Violations

```python
# FATAL - runs in orchestrator context
Skill(skill="spec", args="PLAN 002-phase-001")

# FATAL - vague prompt, may not invoke Skill()
Task(prompt="Execute /spec PLAN for phase-001")

# FATAL - describing workflow instead of tool
Task(prompt="Run the spec planning stage")
```

## Correct Patterns

```python
# Explicit Skill() instruction
Task(
    prompt="Invoke Skill(skill='spec', args='PLAN 002-phase-001'). Return: done",
    model="opus",
    run_in_background=True
)

# Domain skill via delegation
Task(
    prompt="Invoke Skill(skill='build-validate'). Report success/failure. Return: done",
    model="sonnet",
    run_in_background=True
)

# Git inspection (no skill needed)
Task(
    prompt="Read agents/sentinel.md. Check git status. SIGNAL: {signal}",
    model="sonnet",
    run_in_background=True
)
```
