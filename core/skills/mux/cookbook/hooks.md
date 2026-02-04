# Hooks Architecture

PreToolUse hook semantics and skill-scoping configuration for MUX orchestration.

## Overview

Hooks enable enforcement patterns for agent behavior constraints. The primary hook type in MUX is PreToolUse, which validates tool calls before execution.

## PreToolUse Hook Semantics

PreToolUse hooks intercept tool calls before they reach the agent's execution environment.

### Hook Execution Flow

```
Agent → Tool Call Request
         ↓
    PreToolUse Hook
         ↓
    ✓ ALLOW → Execute Tool
    ✗ BLOCK → Return Error
```

### Hook Configuration

Located in `.claude/settings.json`:

```json
{
  "preToolUseHook": {
    "enabled": true,
    "script": ".claude/skills/mux/hooks/pre-tool-use.py",
    "skillScope": ["mux"]
  }
}
```

## Skill-Scoping

Skill-scoping restricts hook enforcement to specific skills.

### Why Skill-Scoping Exists

Without skill-scoping, MUX enforcement rules would apply to ALL agents, including:
- Sub-agents that SHOULD use Read/Write/Edit
- Other skills that need full tool access
- Interactive sessions outside MUX context

### Skill-Scoping Configuration

```json
{
  "preToolUseHook": {
    "skillScope": ["mux"]
  }
}
```

Only agents executing the `mux` skill face tool restrictions.

## Hook Implementation Pattern

```python
def pre_tool_use_hook(tool_name: str, tool_args: dict, context: dict) -> dict:
    """
    Validate tool calls before execution.

    Returns:
        {"action": "allow"} - Execute tool
        {"action": "block", "reason": "..."} - Block with error message
    """

    # Check if skill-scoped
    if context.get("skill") != "mux":
        return {"action": "allow"}

    # MUX orchestrator restrictions
    FORBIDDEN_TOOLS = ["Read", "Write", "Edit", "Grep", "Glob"]

    if tool_name in FORBIDDEN_TOOLS:
        return {
            "action": "block",
            "reason": f"{tool_name} is forbidden for MUX orchestrator. Delegate via Task()."
        }

    return {"action": "allow"}
```

## MUX Hook Rules

### Forbidden Tools
- Read
- Write
- Edit
- Grep
- Glob
- WebSearch
- WebFetch
- NotebookEdit
- Skill (except self-invocation)
- TaskOutput
- TaskStop

### Allowed Tools
- Task
- Bash (restricted commands only)
- AskUserQuestion
- mcp__voicemode__converse
- TaskCreate
- TaskUpdate
- TaskList

### Bash Command Restrictions

Bash tool is allowed, but with command whitelist:

```python
ALLOWED_BASH_COMMANDS = [
    "uv run tools/session.py",
    "uv run tools/verify.py",
    "uv run tools/signal.py",
    "uv run tools/agents.py",
    "mkdir -p",
    "ls"  # ONE-TIME ONLY, not for polling
]
```

## Hook Error Messages

When a forbidden tool is called:

```
PROTOCOL VIOLATION: Read is forbidden for MUX orchestrator.

You must delegate this work via Task():

Task(
    prompt="Read agents/auditor.md. Analyze {file_path}...",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

## Polling Detection

Hooks can detect repeated commands (polling):

```python
def detect_polling(tool_name: str, args: dict, history: list) -> bool:
    """Check if same command run twice."""
    if tool_name == "Bash":
        cmd = args.get("command", "")
        if cmd in history:
            return True  # POLLING DETECTED
    return False
```

## Sub-Agent Exemption

Sub-agents launched via Task() are NOT subject to MUX restrictions:

```python
# Researcher agent CAN use Read/Grep/WebFetch
Task(
    prompt="Read agents/researcher.md. Research product A...",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

The researcher agent runs in its own context without MUX hook enforcement.

## Hook Testing

Verify hook behavior:

```bash
# Test hook with mock tool call
uv run tools/test-hook.py --tool Read --args '{"file_path": "/path"}' --skill mux
```

Expected output:
```
BLOCKED: Read is forbidden for MUX orchestrator
```

## Hook Debugging

Enable hook debugging:

```json
{
  "preToolUseHook": {
    "debug": true
  }
}
```

Output shows:
- Tool call intercepted
- Hook evaluation result
- Allow/block decision
