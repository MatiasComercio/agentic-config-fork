# strict regression checklist

Deterministic yes/no checklist for strict mux protocol regression waves.

## Usage
- Evaluate each item as **PASS** or **FAIL**.
- A strict regression wave is complete only when every required item passes.
- Keep evidence paths project-root-relative.

## A) Leaf-worker contract markers
- [ ] **A01** `mux-subagent` canonical/pi/plugin surfaces explicitly state worker is data-plane only.
  - Files: `canonical/ac-workflow/skills/mux-subagent/body.md`, `canonical/ac-workflow/skills/mux-subagent/body.pi.md`, `packages/pi-ac-workflow/skills/ac-workflow-mux-subagent/SKILL.md`, `plugins/ac-workflow/skills/mux-subagent/SKILL.md`
- [ ] **A02** all `mux-subagent` surfaces keep exact success-response rule: final textual response exactly `0`.
- [ ] **A03** all `mux-subagent` surfaces forbid nested `subagent` calls.
- [ ] **A04** pi/package protocol surfaces forbid worker use of `tmux_agent` / `report_parent`.
- [ ] **A05** required report shape includes `## Executive Summary` and `### Next Steps`.

## B) Artifact-path contract
- [ ] **B01** declared dispatch `report_path` and `signal_path` are documented as project-root-relative.
- [ ] **B02** transcript artifacts use project-root-relative report/signal/summary paths.
- [ ] **B03** gate examples use `extract-summary.py --evidence --evidence-path <path>` and `verify.py --action gate --summary-evidence <path>`.

## C) Guardrail-layer honesty
- [ ] **C01** docs separate strict runtime enforcement from hook enforcement and worker-protocol prose.
- [ ] **C02** strict runtime is documented as explicit/session-scoped (`session.py --strict-runtime --session-key <key>`).
- [ ] **C03** hook guard is documented as harness-scoped `TaskOutput` denial, not universal runtime behavior.
- [ ] **C04** worker protocol prose is documented as contractual guidance, not automatic runtime enforcement.

## D) Transcript artifact presence and required semantics
- [ ] **D01** `protocol/strict-happy-path-transcript.md` exists in canonical/package/plugin copies.
- [ ] **D02** happy-path transcript shows `DECLARE -> DISPATCH -> VERIFY -> ADVANCE` with `gate_status: advance`.
- [ ] **D03** happy-path transcript includes worker signal creation and final `0` response.
- [ ] **D04** `protocol/strict-blocker-path-transcript.md` exists in canonical/package/plugin copies.
- [ ] **D05** blocker-path transcript shows a real `BLOCK` gate result from missing prerequisite/evidence.
- [ ] **D06** blocker-path transcript shows no manual fallback to `ADVANCE` (illegal transition evidence).

## E) Deferment wording cleanup
- [ ] **E01** `assets/mux/protocol/foundation.md` no longer says transcripts/checklists are deferred.
- [ ] **E02** `assets/mux/README.md` no longer says transcripts/checklists are deferred.
- [ ] **E03** `packages/pi-ac-workflow/README.md` no longer says transcript/checklist protocol artifacts remain deferred.

## F) Canonical/package/plugin sync
- [ ] **F01** canonical generation is clean: `uv run python tools/generate_canonical_wrappers.py --check --plugin ac-workflow`.
- [ ] **F02** package protocol files exist: `subagent.md`, `foundation.md`, `guardrail-policy.md`, `strict-happy-path-transcript.md`, `strict-blocker-path-transcript.md`, `strict-regression-checklist.md`.
- [ ] **F03** plugin protocol files exist: `subagent.md`, `foundation.md`, `guardrail-policy.md`, `strict-happy-path-transcript.md`, `strict-blocker-path-transcript.md`, `strict-regression-checklist.md`.

## G) Minimal validation commands
- [ ] **G01** `uv run pytest tests/test_mux_foundation_assets.py tests/test_canonical_generator.py tests/hooks/test_mux_hooks.py`
- [ ] **G02** changed Python files pass lint + typing (`ruff` + `pyright`).
