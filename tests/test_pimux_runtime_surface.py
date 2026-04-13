#!/usr/bin/env python3
"""Surface checks for pimux runtime consistency fixes."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIMUX_INDEX = PROJECT_ROOT / ".pi" / "extensions" / "pimux" / "index.ts"


def test_parent_runtime_auto_finalizes_terminal_child_reports() -> None:
    """The parent runtime should auto-finalize a child after a terminal bridge report."""
    text = PIMUX_INDEX.read_text()
    assert "async function finalizeManagedAgentAfterTerminalReport(" in text
    assert "if (terminalReportForAutoExit && !events.some((event) => event.direction === \"system\" && event.type === \"exited\")) {" in text
    assert "events = await finalizeManagedAgentAfterTerminalReport(launch, ctx);" in text


def test_ui_selectors_render_string_labels_instead_of_objects() -> None:
    """The open/tree pickers should pass display strings to ctx.ui.select."""
    text = PIMUX_INDEX.read_text()
    assert "const choice = await ctx.ui.select(title, items.map((item) => item.label));" in text
    assert "const selected = items.find((item) => item.label === choice);" in text
    assert "const choice = await ctx.ui.select(title, flattened.map((entry) => entry.label));" in text
    assert "const selected = flattened.find((entry) => entry.label === choice);" in text



def test_spawn_identity_seed_uses_role_and_goal_for_clearer_generated_agent_ids() -> None:
    """Generated agent IDs should draw from both role and goal when available."""
    text = PIMUX_INDEX.read_text()
    assert "function buildAgentIdentitySeed(" in text
    assert "buildAgentIdentitySeed(role, goal, prompt)" in text


def test_interactive_agent_actions_prefer_live_targets_and_support_send_selection() -> None:
    """Interactive open/capture/send/kill flows should steer users toward live agents."""
    text = PIMUX_INDEX.read_text()
    assert 'const selected = await chooseAgent(ctx, "Open pimux agent in iTerm", {' in text
    assert 'const selected = await chooseAgent(ctx, "pimux capture", {' in text
    assert 'const selected = await chooseAgent(ctx, "Send message to pimux agent", {' in text
    assert 'const selected = await chooseAgent(ctx, "Kill pimux agent", {' in text
    assert 'requireSession: true' in text
    assert 'message = (await ctx.ui.input(`Send message to ${target}`, "Enter message..."))?.trim() ?? "";' in text



def test_parent_runtime_surfaces_parent_to_child_bridge_messages() -> None:
    """The parent delivery loop should no longer drop outbound bridge messages on the floor."""
    text = PIMUX_INDEX.read_text()
    assert 'if (event.direction !== "child_to_parent") {' not in text
    assert "if (shouldDeliverBridgeEventToParent(event)) {" in text
