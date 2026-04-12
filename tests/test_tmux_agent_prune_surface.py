#!/usr/bin/env python3
"""Source-level checks for tmux-agent prune/archive support."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMUX_AGENT_EXTENSION = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "extensions" / "tmux-agent" / "index.ts"
TMUX_AGENT_SKILL = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "skills" / "ac-workflow-tmux-agent" / "SKILL.md"
TMUX_AGENT_COMMANDS = PROJECT_ROOT / "packages" / "pi-ac-workflow" / "skills" / "ac-workflow-tmux-agent" / "references" / "commands.md"

TMUX_AGENT_SOURCE = TMUX_AGENT_EXTENSION.read_text()
TMUX_AGENT_SKILL_TEXT = TMUX_AGENT_SKILL.read_text()
TMUX_AGENT_COMMANDS_TEXT = TMUX_AGENT_COMMANDS.read_text()


def test_extension_exposes_prune_action_archive_path_and_dry_run() -> None:
    """The extension should expose prune, archive pruned entries, and support dry-run preview."""
    assert 'registryArchivePath = path.join(stateDir, "registry.archive.jsonl")' in TMUX_AGENT_SOURCE
    assert '"prune"' in TMUX_AGENT_SOURCE
    assert 'archivePrunedAgents' in TMUX_AGENT_SOURCE
    assert 'appendJsonLine(registryArchivePath' in TMUX_AGENT_SOURCE
    assert 'olderThan: Type.Optional(Type.String' in TMUX_AGENT_SOURCE
    assert 'dryRun: Type.Optional(Type.Boolean' in TMUX_AGENT_SOURCE
    assert 'inferDryRun' in TMUX_AGENT_SOURCE
    assert 'Archive and remove these' in TMUX_AGENT_SOURCE


def test_extension_parses_older_than_threshold_supports_auto_prune_and_avoids_running_agents() -> None:
    """Prune should use an explicit age threshold, support auto-prune, and avoid touching running agents."""
    assert 'function parseAgeThresholdMs' in TMUX_AGENT_SOURCE
    assert 'Invalid olderThan threshold' in TMUX_AGENT_SOURCE
    assert 'shouldPruneStatus' in TMUX_AGENT_SOURCE
    assert 'mode === "auto" && status.record.status === "exited"' in TMUX_AGENT_SOURCE
    assert 'await pruneManagedAgents(ctx, { scope: "all", olderThan: "1d", dryRun: false, mode: "auto" });' in TMUX_AGENT_SOURCE
    assert 'next.agents = next.agents.filter((entry) => !prunedIds.has(entry.agentId));' in TMUX_AGENT_SOURCE


def test_docs_advertise_prune_dry_run_confirmation_and_auto_prune() -> None:
    """User-facing docs should mention dry-run, confirmation, and auto-prune behavior."""
    assert '/tmux-agent prune' in TMUX_AGENT_SKILL_TEXT
    assert '- `prune`' in TMUX_AGENT_COMMANDS_TEXT
    assert '--dry-run' in TMUX_AGENT_SOURCE
    assert 'auto-prunes entries whose effective state is missing or terminated' in TMUX_AGENT_COMMANDS_TEXT
    assert 'The extension auto-prunes registry entries whose effective state is missing or terminated' in TMUX_AGENT_SKILL_TEXT
