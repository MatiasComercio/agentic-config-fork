# pimux patterns

## Single worker

Use one child when the task is bounded but should stay long-lived or visually inspectable.

## Scout -> planner replacement

1. spawn a `scout`-style child to inventory the codebase
2. let it run and wait for explicit `closeout`
3. pass the artifact or report path into a `planner`-style child
4. let the planner return the execution plan

Do not rely on prose inference between steps; hand off file paths or bounded summaries.
Do not keep the parent blocked with sleep loops or repeated pings while waiting; inspect only at a real handoff, live-watch request, or suspected problem.

## Team / brainstorm pattern

Use one orchestrator child plus a few role-specific children.

Rules:
- explicit roles
- explicit message routing
- explicit stop conditions
- no ambient cross-talk unless deliberately instructed

## mux family adaptation

Use pimux as the control-plane runtime for:
- mux
- mux-ospec
- mux-roadmap

Keep wrappers thin:
- wrapper skill owns prompt and file conventions
- pimux owns tmux launch, messaging, settlement, and visual supervision

## Explicit trigger discipline

If a pimux-family skill is explicitly invoked, follow the pattern all the way:
- read the required reference
- spawn the child or hierarchy
- hand off via files
- wait asynchronously for bridge reports

Do not stop at planning to spawn, and do not replace the run with parent-side domain work.
