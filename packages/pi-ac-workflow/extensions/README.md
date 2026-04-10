# extensions

Package-local pi extensions exported by `@agentic-config/pi-ac-workflow`.

## Current extension set
- `tmux-agent/`
  - `index.ts`: exact repo-owned migration of the proven global `tmux-agent` extension
  - preserves the shipped `/tmux-agent` command and `tmux_agent` tool surface without narrowing the action set
  - enforces direct-child-only bridge authority plus explicit success settlement (`closeout` + child exit), explicit non-success settlement, bounded non-terminal `progress`, and protocol-violation handling for undeclared exits
  - surfaces settled bridge state (`running`, `settled_completion`, `settled_failure`, `settled_blocked`, `settled_waiting_on_parent`, `protocol_violation`) through status/report paths
  - preserves managed-session registry/audit state, private parent-child bridge flow, hierarchy/root tracking, managed visuals, debate channels, and peer-mode coordination
- `strict-mux-runtime/`
  - `index.js`: workflow-owned strict mux runtime guard for deliberately activated strict sessions
  - activates only after `assets/mux/tools/session.py --strict-runtime` writes the session-key-scoped activation artifacts for the current pi session
  - consumes the shared mux ledger/gate substrate to fail closed on missing/invalid strict runtime state, validate the single declared strict `subagent` dispatch shape, and block coordinator-side mutations outside bounded orchestration paths

The current workflow package now ships both package-local workflow extensions above.