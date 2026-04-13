---
name: pimux-roadmap
description: "Runs a roadmap coordinator on top of the local `pimux` extension with tmux-backed phase supervision, explicit messaging, and session-scoped hierarchy inspection. Triggers on keywords: pimux roadmap, roadmap with pimux, tmux roadmap coordinator"
project-agnostic: false
allowed-tools:
  - Read
  - Bash
  - pimux
  - subagent
---

# pimux-roadmap

Use this wrapper when you want a roadmap-level coordinator in tmux.

## Mandatory trigger behavior

If the user explicitly triggers `pimux-roadmap`, the parent must keep the work in the tmux-backed roadmap lane.

Required sequence:
1. resolve the roadmap path and relevant phase handoff
2. read [../pimux/references/protocol.md](../pimux/references/protocol.md)
3. spawn the roadmap coordinator or phase-owning `pimux` child before doing substantive roadmap execution work
4. keep the parent in control-plane only except for narrow artifact preparation and consolidation

Do not execute the roadmap directly in the parent while this skill is active.

## Rules

- roadmap coordinator owns the control-plane
- phase workers report through explicit `pimux` bridge events only
- keep roadmap mirrors and phase artifacts as file-based handoff surfaces
- use current-session `tree` / `status` to supervise the active hierarchy
- use `open` only for focused live inspection

Read [../pimux/references/protocol.md](../pimux/references/protocol.md) before running a nested roadmap hierarchy.
