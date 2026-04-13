#!/usr/bin/env python3
"""Surface checks for pimux runtime consistency fixes."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIMUX_INDEX = PROJECT_ROOT / ".pi" / "extensions" / "pimux" / "index.ts"
PIMUX_RENDER = PROJECT_ROOT / ".pi" / "extensions" / "pimux" / "render.ts"
PIMUX_REGISTRY = PROJECT_ROOT / ".pi" / "extensions" / "pimux" / "registry.ts"


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



def test_child_inbox_uses_exact_message_content_and_steering_delivery() -> None:
    """Child delivery should preserve raw payloads and steer queued messages deterministically."""
    index_text = PIMUX_INDEX.read_text()
    render_text = PIMUX_RENDER.read_text()
    assert "const queuedChildInboxEventIds = new Set<string>();" in index_text
    assert 'pi.sendUserMessage(message, { deliverAs: "steer" });' in index_text
    assert 'return event.message?.trim() || event.summary?.trim() || "";' in render_text



def test_kill_runtime_cascades_to_live_descendants_before_parent_termination() -> None:
    """Killing a parent should recursively terminate live descendants first."""
    text = PIMUX_INDEX.read_text()
    assert "function collectDescendantStatuses(" in text
    assert "async function requestManagedAgentShutdown(" in text
    assert "async function terminateManagedAgentRecord(" in text
    assert "terminated because ancestor" in text
    assert 'event.type === "shutdown_request"' in text
    assert "shouldShutdownTerminatedAgent" in text



def test_command_surface_includes_canned_smoke_nested_mode() -> None:
    """The command surface should expose the canned nested smoke guide mode."""
    text = PIMUX_INDEX.read_text()
    assert '"  /pimux smoke-nested [--prefix ID] [--output PATH]"' in text
    assert 'case "smoke-nested": {' in text
    assert '"## Wrapper exit rules"' in text
    assert '"- use `failure` when a direct child settled `settled_failure` or `protocol_violation`"' in text
    assert '"- do not make the wrapper itself the killed parent in a cascade test; kill a disposable child-parent pair under the wrapper instead"' in text



def test_closeout_guard_suggests_non_success_terminal_reports_for_wrappers() -> None:
    """Supervisors should get actionable guidance when closeout is blocked by non-success child outcomes."""
    index_text = PIMUX_INDEX.read_text()
    registry_text = PIMUX_REGISTRY.read_text()
    assert "suggestSupervisorTerminalReportKind" in registry_text
    assert 'Suggested terminal report: ${suggestedKind}.' in index_text
    assert 'Use report_parent(${suggestedKind}) if these child outcomes are intentional.' in index_text
    assert 'Wait for unsettled children to reach terminal settlement before using report_parent(closeout).' in index_text
