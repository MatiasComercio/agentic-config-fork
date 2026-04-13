# pimux protocol

## Messaging model

- parent -> child: explicit bridge inbox events via `send_message`
- child -> parent: explicit bridge reports via `report_parent`
- one hop only: L2 reports to L1, L1 reports to L0

## Authority model

Only the authoritative direct child session for a bridge may call `report_parent`.

Implications:
- helper subagents are local-only
- helper completion is not settlement
- helper misuse of `pimux` / `report_parent` is invalid

## Settlement model

- `progress` is non-terminal
- `closeout + exit` -> `settled_completion`
- `failure + exit` -> `settled_failure`
- `blocker + exit` -> `settled_blocked`
- `question + exit` -> `settled_waiting_on_parent`
- exit without terminal declaration -> `protocol_violation`

After a terminal child report, the pimux runtime should finalize the managed session promptly instead of leaving the child alive in an ambiguous post-closeout state.
The child should not keep chatting or continue work after emitting a terminal report.

## Nested orchestrator rule

If a child spawns direct pimux children, it must not emit `closeout` until every direct pimux child is `settled_completion`.

## Explicit skill-trigger rule

When the parent session entered this family through an explicit `pimux`, `pimux-mux`, `pimux-ospec`, or `pimux-roadmap` skill trigger, that trigger is a runtime commitment, not a suggestion.

- The parent must stay control-plane only.
- The parent may read protocol references, prepare handoff files, and spawn or message children.
- The substantive domain work must be carried by the spawned authoritative child session(s).
- Do not replace the requested pimux flow with a direct parent-side answer, analysis, or implementation.
- If the chosen wrapper is wrong for the task, say so and stop or switch cleanly; do not silently degrade to a non-pimux workflow.

## Supervision pacing rule

Default parent behavior is asynchronous.

After dispatch, the parent should let the child work instead of busy-waiting with sleep loops, repeated `status` checks, or repeated nudges.

Inspect or intervene only when:
- the child emits a bridge report
- the user asks to inspect live progress
- a real downstream handoff now depends on settlement
- there is concrete evidence of a stall, blocker, or protocol problem

One targeted `status` / `capture` check at a real decision point is fine. Continuous polling is not.

## Session scope rule

Default supervision is scoped to the current session hierarchy. Broaden scope only when explicitly needed.
