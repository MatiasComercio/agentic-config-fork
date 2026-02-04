# Phase Execution

Detailed phase-by-phase execution guide for MUX orchestration.

## Phase 0: Confirmation

CONFIRM to user (voice and text by default) that you are starting the mux process using the `mux` skill explicitly.

Voice example:
```python
mcp__voicemode__converse(
    message="Starting mux for {topic}",
    voice="af_heart",
    tts_provider="kokoro",
    speed=1.25,
    wait_for_response=False
)
```

## Phase 1: Decomposition

Parse TASK from the arguments provided. DO NOT gather additional context yourself.

Extract from TASK text:
- `LEAN_MODE`: true if "lean" keyword present
- `RESEARCH_SUBJECTS`: Products/systems mentioned in TASK
- `OUTPUT_TYPE`: roadmap | spec | analysis | learnings (infer from TASK)

### Context Gathering Pattern

**CRITICAL:** If you need more context to decompose the task:
1. DO NOT use Read/Grep/WebFetch yourself
2. DO launch an auditor agent to gather context
3. Wait for auditor signal, then proceed with decomposition

```python
# If context needed, delegate to auditor FIRST
Task(
    prompt="""Read agents/auditor.md for protocol.

TASK: Gather context for task decomposition
- Analyze relevant codebase areas
- Fetch any referenced URLs/issues
OUTPUT: {session_dir}/audit/task-context.md
SIGNAL: {session_dir}/.signals/000-context.done

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

Voice update:
```python
mcp__voicemode__converse(
    message=f"Starting mux for {topic}",
    voice="af_heart",
    tts_provider="kokoro",
    speed=1.25,
    wait_for_response=False
)
```

## Phase 2: Fan-Out Research

Launch ALL workers in ONE message for parallelism.

```python
# Workers (ALL launched here)
for subject in subjects:
    Task(
        prompt=f"""Read agents/researcher.md for protocol.

TASK: Research {subject}
OUTPUT: {session_dir}/research/{subject.lower().replace(' ', '-')}.md
SIGNAL: {session_dir}/.signals/research-{subject.lower().replace(' ', '-')}.done

FINAL: Return EXACTLY: done""",
        subagent_type="general-purpose",
        model="sonnet",
        run_in_background=True
    )

# Monitor (launched in SAME message)
Task(
    prompt=f"""Read agents/monitor.md for protocol.

SESSION: {session_dir}
EXPECTED: {len(subjects)}

Use poll-signals.py to track completion.

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="haiku",
    run_in_background=True
)

# Checkpoint (MANDATORY)
# ✓ {len(subjects)} workers launched
# ✓ Monitor launched in same message
# ✓ Monitor has --expected {len(subjects)}
# ✓ Continuing immediately

voice(f"{len(subjects)} research workers launched with monitor")
```

## Phase 3: Fan-Out Audits

Same pattern as Phase 2, using `agents/auditor.md`.

```python
# Workers
for audit_task in audit_tasks:
    Task(
        prompt=f"""Read agents/auditor.md for protocol.

TASK: {audit_task}
OUTPUT: {audit_output_path}
SIGNAL: {audit_signal_path}

FINAL: Return EXACTLY: done""",
        subagent_type="general-purpose",
        model="sonnet",
        run_in_background=True
    )

# Monitor (SAME message)
Task(
    prompt=f"""Read agents/monitor.md for protocol.

SESSION: {session_dir}
EXPECTED: {len(audit_tasks)}

Use poll-signals.py to track completion.

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="haiku",
    run_in_background=True
)
```

## Phase 2-3: Monitoring

Orchestrator continues IMMEDIATELY - never waits.

The monitor agent handles completion tracking via poll-signals.py.

```python
Task(
    prompt=f"""Read agents/monitor.md for protocol.

SESSION: {session_dir}
EXPECTED: {expected_count}

Use poll-signals.py to track completion.

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="haiku",
    run_in_background=True
)
```

## Phase 4: Consolidation

Only if total size exceeds 80KB.

```bash
uv run tools/verify.py "$SESSION_DIR" --action total-size
```

If > 80KB, launch consolidator:

```python
Task(
    prompt=f"""Read agents/consolidator.md for protocol.

TASK: Consolidate findings from research and audits
SESSION: {session_dir}
OUTPUT: {session_dir}/consolidated.md
SIGNAL: {session_dir}/.signals/consolidation.done

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

## Phase 5: Coordination

### Standard Mode

Launch coordinator (opus) who delegates to writers.

```python
Task(
    prompt=f"""Read agents/coordinator.md for protocol.

TASK: Design deliverable structure and delegate to writers
SESSION: {session_dir}
OUTPUT: {session_dir}/coordination.md
SIGNAL: {session_dir}/.signals/coordination.done

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="opus",
    run_in_background=True
)
```

### Lean Mode

Launch single writer (sonnet) directly.

```python
Task(
    prompt=f"""Read agents/writer.md for protocol.

TASK: Write {deliverable_name}
SESSION: {session_dir}
OUTPUT: {session_dir}/deliverables/{deliverable_name}.md
SIGNAL: {session_dir}/.signals/writer.done

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

## Phase 6: Verification

```bash
uv run tools/verify.py "$SESSION_DIR" --action summary
```

Output shows:
- Signals completed
- Output files created
- Total size
- Missing signals (if any)

## Phase 6.5: Sentinel Review

MANDATORY quality gate.

```python
Task(
    prompt=f"""Read agents/sentinel.md for protocol.

TASK: Review session quality against pillars
SESSION: {session_dir}
PILLARS: {quality_pillars}
OUTPUT: {session_dir}/sentinel-review.md
SIGNAL: {session_dir}/.signals/sentinel.done

FINAL: Return EXACTLY: done""",
    subagent_type="general-purpose",
    model="sonnet",
    run_in_background=True
)
```

If FAIL: Use AskUserQuestion to let user decide:
```python
AskUserQuestion(
    questions=[{
        "question": "Sentinel review found gaps. How to proceed?",
        "header": "Quality Gate",
        "options": [
            {"label": "Proceed anyway", "description": "Accept current quality and continue"},
            {"label": "Address gaps", "description": "Re-run affected phases to fix issues"},
            {"label": "Abort", "description": "Stop session without delivering"}
        ],
        "multiSelect": False
    }]
)
```

## Interactive Gates (Critical Decision Points)

Use AskUserQuestion ONLY at these points:
1. **Sentinel failure** - proceed/address/abort
2. **Consolidation decision** - when output > 80KB
3. **Error recovery** - timeout/failure handling

Normal phase transitions: voice announcement + auto-proceed.

## Error Recovery Patterns

| Error Type | Recovery Action |
|------------|----------------|
| Agent timeout | Check partial signal, relaunch with tighter scope |
| Monitor timeout | Launch NEW monitor, never self-monitor |
| Coordinator context limit | Run consolidation first, retry |

## Voice Protocol Timing

Update at:
- Phase start (confirmation)
- Milestones (workers launched)
- Completion (sentinel review done)
- Errors (recovery actions)

```python
mcp__voicemode__converse(
    message="{update}",
    voice="af_heart",
    tts_provider="kokoro",
    speed=1.25,
    wait_for_response=False
)
```
