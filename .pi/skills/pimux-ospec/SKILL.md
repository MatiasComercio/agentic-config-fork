---
name: pimux-ospec
description: "Runs a spec-phase orchestrator on top of the local `pimux` extension with tmux-backed stage coordination and explicit bridge settlement. Triggers on keywords: pimux ospec, ospec with pimux, tmux spec orchestrator"
project-agnostic: false
allowed-tools:
  - Read
  - Bash
  - pimux
  - subagent
---

# pimux-ospec

Use this wrapper when you want a spec-stage orchestrator in tmux.

## Mandatory trigger behavior

If the user explicitly triggers `pimux-ospec`, the parent must keep the work in the tmux-backed spec orchestration lane.

Required sequence:
1. resolve the target spec path
2. read [../pimux/references/patterns.md](../pimux/references/patterns.md)
3. if the spec path is missing or wrong, block immediately instead of improvising
4. otherwise spawn the stage-owning `pimux` coordinator or stage child before doing substantive stage work

Do not run the spec-stage execution directly in the parent while this skill is active.

## Rules

- keep stage ownership explicit
- keep stage artifacts on disk and pass paths between agents
- use `pimux report_parent` only from the authoritative tmux coordinator for that stage layer
- never let stage helpers call `pimux` or `report_parent`
- use `status` before any upward consolidation or closeout

Read [../pimux/references/patterns.md](../pimux/references/patterns.md) for the scout -> planner replacement and nested-orchestrator pattern.
