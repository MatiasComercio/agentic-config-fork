#!/usr/bin/env python3
"""Source-level checks for tmux-agent session scoping and strict nested orchestration."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMUX_AGENT_EXTENSION = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "index.ts"
TMUX_AGENT_SKILL = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "skills" / "ac-workflow-tmux-agent" / "SKILL.md"
TMUX_AGENT_COMMANDS = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "skills" / "ac-workflow-tmux-agent" / "references" / "commands.md"

TMUX_AGENT_SOURCE = TMUX_AGENT_EXTENSION.read_text()
TMUX_AGENT_SKILL_TEXT = TMUX_AGENT_SKILL.read_text()
TMUX_AGENT_COMMANDS_TEXT = TMUX_AGENT_COMMANDS.read_text()


def test_extension_blocks_orchestrator_closeout_until_direct_children_settle() -> None:
    """Nested orchestrators should not be allowed to close out while direct children remain unsettled."""
    assert "assertDirectChildrenSettledForCloseout" in TMUX_AGENT_SOURCE
    assert "Cannot close out" in TMUX_AGENT_SOURCE
    assert "direct tmux children must be settled_completion first" in TMUX_AGENT_SOURCE
    assert 'status.record.parentAgentId === agentId' in TMUX_AGENT_SOURCE


def test_extension_defaults_visibility_to_current_session_scope_and_exposes_tree_nodes() -> None:
    """List/tree surfaces should default to session scope and return navigable tree metadata."""
    assert 'scope: hasFlag(parsed, "all") ? "all" : rootAgentId ? "root" : "session"' in TMUX_AGENT_SOURCE
    assert 'No managed agents available in the current session hierarchy' in TMUX_AGENT_SOURCE
    assert 'const tree = await treeManagedAgents(ctx, options);' in TMUX_AGENT_SOURCE
    assert 'nodes: tree.nodes' in TMUX_AGENT_SOURCE
    assert '"navigate"' in TMUX_AGENT_SOURCE


def test_child_protocol_and_docs_require_patient_control_plane_behavior() -> None:
    """Prompt and doc surfaces should mirror strict control-plane expectations."""
    assert "Do not send repeated impatient nudges." in TMUX_AGENT_SOURCE
    assert "You must explicitly tell local helpers not to call tmux_agent or report_parent." in TMUX_AGENT_SOURCE
    assert "A tmux orchestrator must not emit `closeout` while any direct tmux child remains running or otherwise unsettled." in TMUX_AGENT_SKILL_TEXT
    assert "`navigate` to select a node from the current tree" in TMUX_AGENT_COMMANDS_TEXT
