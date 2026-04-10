# Phase Lifecycle Guidance

Use this reference when tmux-backed agents are coordinating sequential phases of work.

## Best default pattern

For multi-phase work, prefer:

1. write or update a short plan/status document
2. spawn one agent for the current phase
3. require explicit terminal declaration (`closeout` for success, or explicit non-success)
4. process the report
5. clean up the finished agent promptly
6. launch the next phase

This is usually better than keeping one broad worker alive across many different phases.

## Recommended defaults

- default to **headless**
- use `notificationMode: "notify-and-follow-up"` when phase chaining matters
- treat `notificationMode: "notify-and-follow-up"` as the settled end-of-session handoff for the child after explicit terminal declaration plus child exit, not as a stage-level or per-turn milestone
- local helper or ordinary subagent completion inside a tmux-agent is local input only; do not emit `closeout` until the tmux-agent itself has consolidated that work and is ready to stop
- use `open_visual` only when the user explicitly wants live inspection or the running agent is worth monitoring
- keep one clear mission per agent

## Implementation phase template

Use when a phase should mainly change code.

Prompt ingredients:
- read `AGENTS.md` and the current plan file
- implement **this phase only**
- keep scope narrow
- run exact verification commands
- do not commit or push unless explicitly requested
- emit `report_parent` with `reportKind: closeout` (plus bounded reportMarkdown when needed) before stopping
- do not emit the tmux-agent closeout early; make the tmux-agent report in the CORRECT moment, when it completes the ENTIRE phase work

Expected report shape:
1. files changed
2. what was delivered
3. verification results
4. ready-for-next-phase handoff
5. blockers or risks

## Verification / remediation phase template

Use after implementation when completeness matters.

Prompt ingredients:
- verify every listed requirement explicitly
- if anything is missing or only partially implemented, remediate it before stopping
- run targeted verification after remediation
- emit explicit pass/fail-per-requirement accounting

Expected report shape:
1. remediation summary
2. pass/fail-per-requirement accounting
3. verification results
4. recommended next actions
5. blockers or risks

## Browser QA phase template

Use for Playwright CLI or browser-level validation.

Prompt ingredients:
- read prior phase artifacts
- prefer QA/reporting only
- do not change code unless a critical blocker prevents meaningful QA
- save a QA artifact under a predictable output path
- emit `report_parent` with `reportKind: closeout` before stopping

Expected report shape:
1. routes/scenarios tested
2. pass/fail findings
3. screenshots/artifacts produced
4. blockers or regressions
5. recommended next actions

## Mid-flight scope updates

When the user adds new requirements while an agent is already running:

1. update the shared plan/status document first
2. send the running agent a short message pointing at the updated plan
3. state whether the new requirement should be implemented now or only enforced in a later verification phase

## Completion processing checklist

When a phase completes:

1. read the settled terminal artifact (`closeout`, `failure`, `blocker`, or exited `question`)
2. if anything looks suspicious, verify with `status` and `capture`
3. if the child exited without valid terminal declaration, treat it as `protocol_violation` before proceeding
4. update the plan/status document
5. if your workflow uses voice, announce only meaningful milestones such as phase completion or required input
6. close visuals if desired
7. kill the finished agent promptly
8. launch the next phase

The parent should not proceed because of intermediate capture noise, a stage subagent result, a local helper completion, or a partial artifact. Proceed only after settled tmux state is explicit and verified.

## Protocol violation handling

If an agent appears done but failed to emit a valid terminal declaration (`closeout` or explicit non-success), or emitted `closeout` too early:

1. inspect the real live state with `status` and `capture`
2. capture enough terminal evidence to justify your decision
3. document the protocol violation in the plan/status document
4. only continue if the completion state is unambiguous or the human explicitly instructs you to proceed
5. strengthen the next phase prompt with an explicit requirement not to stop without valid terminal declaration, not to treat local helper completion as final completion, and not to emit `closeout` before the ENTIRE phase work is complete

## Important anti-patterns

Avoid:
- trusting one completion or failure artifact blindly
- treating `close_visual` as guaranteed cleanup
- leaving finished agents alive after their output is already harvested
- halting autonomous progression because of unrelated pre-existing repo failures when phase-relevant verification is green
- combining implementation, remediation, and QA into one large agent when accountability matters

## Cleanup note

`close_visual` is best-effort visual cleanup.

`kill` is the authoritative cleanup step.
