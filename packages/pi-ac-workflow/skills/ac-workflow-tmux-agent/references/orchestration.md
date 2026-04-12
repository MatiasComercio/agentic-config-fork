# Orchestration Guidance

## Goal

Use persistent tmux-backed agents to create clear ownership across a small multi-agent hierarchy.

## Base rule

Hierarchy should reduce confusion.

Only create additional agents when they improve focus, speed, or separation of concerns.

## Recommended pattern

### Chief of Staff

Responsibilities:

- understand the human objective
- break work into departments or workstreams
- create or direct heads
- collect summaries
- escalate only the decisions that matter

### Head of X

Responsibilities:

- own one domain
- break work into narrow tasks
- create doers only when necessary
- review child output before reporting upward
- wait for direct child settlement instead of pushing repeated impatient nudges

### Doer

Responsibilities:

- execute one bounded task
- return compact results
- escalate blockers instead of improvising broad scope changes

## Communication rules

### Downward

Downward instructions should specify:

- mission
- constraints
- expected deliverable
- response format
- when to escalate

### Upward

Upward reports should usually contain:

1. status
2. result or finding
3. blockers
4. next recommendation

### Terminal settlement rules

- Success requires explicit `report_parent` with `reportKind: closeout`, then child exit.
- An orchestrator must not emit `closeout` while any direct tmux child remains running or otherwise unsettled.
- Explicit non-success terminal declarations are `failure`, `blocker`, and exited `question`.
- `progress` is non-terminal and non-follow-up by default.
- Only the authoritative direct child for a bridge may emit terminal declarations or the authoritative exit signal for that bridge.
- Local helper or ordinary subagent completion inside a tmux-agent stays local to that tmux-agent and must not be treated as parent-visible settlement.
- Exit without valid terminal declaration settles as `protocol_violation`.
- Supervisors should verify settled state with `status` before phase chaining.

## Spawn rules

- Chiefs of Staff may spawn heads and a few specialist peers.
- Heads may spawn doers and temporary reviewers or analysts.
- Doers should rarely spawn children unless explicitly allowed.

## Phase-oriented work

When the work is sequential rather than hierarchical, prefer **one agent per phase** instead of one catch-all worker.

The pattern that tends to work best is:

1. implementation phase
2. verification/remediation phase
3. browser QA phase

Why this works:
- implementation can focus on building
- verification can check whether the full scope was actually implemented
- browser QA can validate UX without being mixed into coding noise

For autonomous chaining, prefer:
- a small plan/status document outside the child session
- `notificationMode: "notify-and-follow-up"`
- explicit terminal declarations (`closeout` or declared non-success) plus child exit
- prompt cleanup that kills each phase agent after its output is harvested

## Anti-patterns

Avoid:

- large flat swarms with weak ownership
- vague roles like helper-1 and helper-2
- frequent noisy status spam
- repeated impatient nudges to children when no timeout or explicit blocker has been reached
- using more agents to compensate for poor prompts
- combining implementation, remediation, and QA in one large agent when correctness matters
- trusting one completion or failure artifact without checking settled bridge state
- inferring success from quiet sessions, observer capture, or last-turn text
- treating a local helper or subagent result as if the supervising tmux-agent had completed
- letting an agent stop without explicit `closeout` or a declared non-success terminal path
- leaving finished phase agents alive after their output has already been harvested

## Peer debates

Peer communication is explicit, not ambient.

Use debate channels only when short bounded cross-peer exchange is genuinely useful.

Available modes:

- `alone`: no peer delivery
- `all`: all active peers under the same root
- `subset`: only explicit participants
- `direct`: one targeted peer set for a narrow exchange

Defaults:

- default peer behavior is isolated
- open a debate channel before expecting peer delivery
- keep inline debate summaries short
- use bounded report artifacts for long-form reasoning

## Human visibility

Open iTerm tabs when:

- the user explicitly asks
- a particular agent is worth monitoring live
- a supervisor is coordinating several children and the human wants to inspect it

Keep agents headless when:

- they are doing narrow background work
- no live oversight is needed
- extra tabs would add noise
