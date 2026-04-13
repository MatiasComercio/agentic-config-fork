#!/usr/bin/env python3
"""Surface checks for local pimux skills and references."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIMUX_SKILL = PROJECT_ROOT / ".pi" / "skills" / "pimux" / "SKILL.md"
PIMUX_COMMANDS = PROJECT_ROOT / ".pi" / "skills" / "pimux" / "references" / "commands.md"
PIMUX_PROTOCOL = PROJECT_ROOT / ".pi" / "skills" / "pimux" / "references" / "protocol.md"
PIMUX_PATTERNS = PROJECT_ROOT / ".pi" / "skills" / "pimux" / "references" / "patterns.md"
PIMUX_MUX = PROJECT_ROOT / ".pi" / "skills" / "pimux-mux" / "SKILL.md"
PIMUX_OSPEC = PROJECT_ROOT / ".pi" / "skills" / "pimux-ospec" / "SKILL.md"
PIMUX_ROADMAP = PROJECT_ROOT / ".pi" / "skills" / "pimux-roadmap" / "SKILL.md"


def test_core_skill_requires_explicit_messaging_settlement_and_trigger_commitment() -> None:
    """The base skill should document explicit messaging, authority, settlement, and trigger discipline."""
    text = PIMUX_SKILL.read_text()
    protocol = PIMUX_PROTOCOL.read_text()
    assert "Parent -> child messaging uses `pimux send_message`." in text
    assert "Child -> parent reporting uses `pimux report_parent`." in text
    assert "Parent-side interface delivery should also show bridge message traffic concisely; parent -> child messages stay visible without forcing an extra turn." in text
    assert "`list`, `tree`, and `navigate` should keep agent IDs visible while adding role/goal labels, clearer hierarchy connectors, and best-effort safe styling when the host interface supports it." in text
    assert "Success settles only after `report_parent(closeout)` plus child exit." in text
    assert "live-session actions such as `open`, `capture`, `send`, and `kill` should prefer currently running agents in interactive selectors" in text
    assert "If the user explicitly invokes `pimux` or a `pimux-*` wrapper, treat that as a commitment to the pimux runtime." in text
    assert "Only the authoritative direct child session for a bridge may call `report_parent`." in protocol
    assert "that trigger is a runtime commitment, not a suggestion." in protocol
    assert "Default supervision is scoped to the current session hierarchy." in protocol
    assert "the supervising wrapper should propagate the matching terminal kind and exit cleanly instead of forcing `closeout` or relying on manual kill" in protocol
    assert "For cascade-kill testing, keep the wrapper alive and kill a disposable child parent/descendant pair under it rather than making the wrapper itself the killed parent." in protocol


def test_commands_reference_exposes_minimal_surface() -> None:
    """The commands reference should document the reduced pimux surface."""
    text = PIMUX_COMMANDS.read_text()
    assert "- `spawn`" in text
    assert "- `open`" in text
    assert "- `tree`" in text
    assert "- `send_message`" in text
    assert "- `report_parent`" in text
    assert "Parent-side interface delivery should also show parent -> child bridge messages as concise pimux events without triggering an extra turn." in text
    assert "list/tree/navigation labels keep the agent ID visible while adding role/goal context for easier selection" in text
    assert "interactive `open`, `capture`, `send`, and `kill` pickers should prefer live agents when no target is provided" in text
    assert "- `kill`" in text


def test_wrapper_skills_point_back_to_core_pimux_contract() -> None:
    """The mux/ospec/roadmap wrappers should stay thin, strict, and reuse the core pimux docs."""
    patterns = PIMUX_PATTERNS.read_text()
    assert "Use pimux as the control-plane runtime for:" in patterns
    assert "If a pimux-family skill is explicitly invoked, follow the pattern all the way:" in patterns

    mux_text = PIMUX_MUX.read_text()
    assert "If the user explicitly triggers `pimux-mux`, the parent must actually run the task through `pimux`." in mux_text
    assert "Do not satisfy the request by directly reading files and answering from the parent." in mux_text

    ospec_text = PIMUX_OSPEC.read_text()
    assert "If the user explicitly triggers `pimux-ospec`, the parent must keep the work in the tmux-backed spec orchestration lane." in ospec_text
    assert "Do not run the spec-stage execution directly in the parent while this skill is active." in ospec_text

    roadmap_text = PIMUX_ROADMAP.read_text()
    assert "If the user explicitly triggers `pimux-roadmap`, the parent must keep the work in the tmux-backed roadmap lane." in roadmap_text
    assert "Do not execute the roadmap directly in the parent while this skill is active." in roadmap_text

    for text in (mux_text, ospec_text, roadmap_text):
        assert "pimux" in text
        assert "protocol" in text or "patterns" in text
