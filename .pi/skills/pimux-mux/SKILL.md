---
name: pimux-mux
description: "Runs a mux-style coordinator on top of the local `pimux` extension with explicit tmux messaging, one-hop reporting, and file-path context handoff. Triggers on keywords: pimux mux, mux with pimux, tmux mux coordinator"
project-agnostic: false
allowed-tools:
  - Read
  - Bash
  - pimux
  - subagent
---

# pimux-mux

Use this wrapper when you want mux-style orchestration but with tmux-backed Pi agents instead of the older strict mux runtime.

## Mandatory trigger behavior

If the user explicitly triggers `pimux-mux`, the parent must actually run the task through `pimux`.

Required sequence:
1. read [../pimux/references/protocol.md](../pimux/references/protocol.md)
2. prepare any brief or artifact paths needed for file-path handoff
3. spawn the appropriate `pimux` child or hierarchy before doing substantive domain analysis
4. keep the parent control-plane only and let child sessions do the substantive work

Do not satisfy the request by directly reading files and answering from the parent.
For bounded research or comparison work, spawn at least a scout child; add a planner child when the synthesis benefits from a second handoff step.

## Rules

- use `pimux` for launch, messaging, status, capture, and settlement
- use one control-plane orchestrator at each tmux layer
- keep helper subagents local-only
- hand off context by file path whenever possible
- prefer scout -> planner -> worker style decomposition when useful
- after dispatch, let children run; do not block the parent with sleep loops, constant polling, or managerial nudges unless live supervision or an immediate handoff requires it

Load [../pimux/references/protocol.md](../pimux/references/protocol.md) before spawning a hierarchy.
