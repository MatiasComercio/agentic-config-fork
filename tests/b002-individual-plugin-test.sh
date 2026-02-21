#!/usr/bin/env bash
# B-002: Individual Plugin Testing
# Requires interactive Claude CLI. Run each block manually.
# SC-3a: marketplace addable
# SC-3b: each plugin individually installable
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGINS=(agentic agentic-spec agentic-mux agentic-git agentic-review agentic-tools)

echo "=== SC-1: Validate marketplace ==="
echo "RUN: claude plugin validate '$REPO_ROOT'"
echo ""

echo "=== SC-3a: Add local marketplace ==="
echo "RUN (inside claude session):"
echo "  /plugin marketplace add $REPO_ROOT"
echo ""

echo "=== SC-3b: Install each plugin individually ==="
for p in "${PLUGINS[@]}"; do
  echo "RUN: claude plugin install ${p}@agentic-plugins"
done
echo ""

echo "=== Per-plugin verification ==="
for p in "${PLUGINS[@]}"; do
  echo "--- Plugin: $p ---"
  echo "Load: claude --plugin-dir $REPO_ROOT/plugins/$p"
  echo "Check:"
  echo "  1. /help -- verify commands from $p appear"
  echo "  2. Skills discoverable (if plugin has skills/)"
  echo "  3. Agents visible in /agents (if plugin has agents/)"
  echo ""

  # Expected assets per plugin
  case "$p" in
    agentic)
      echo "  Commands (10): agentic, agentic-setup, agentic-status, agentic-update,"
      echo "    agentic-migrate, agentic-export, agentic-import, agentic-share, branch, spawn"
      echo "  Skills (7): cpc, dr, had, human-agentic-design, command-writer, skill-writer, hook-writer"
      echo "  Agents (6): agentic-customize, agentic-migrate, agentic-setup, agentic-status, agentic-update, agentic-validate"
      echo "  Hooks (2): dry-run-guard, git-commit-guard"
      ;;
    agentic-spec)
      echo "  Commands (3): spec, o_spec, po_spec"
      echo "  Skills (0): none"
      echo "  Agents (2): spec agents"
      echo "  Hooks (0): none"
      ;;
    agentic-mux)
      echo "  Commands (2): mux, milestone"
      echo "  Skills (5): agent-orchestrator-manager, product-manager, mux, mux-ospec, mux-subagent"
      echo "  Agents (0): none"
      echo "  Hooks (0 plugin-level): skill-level hooks only"
      ;;
    agentic-git)
      echo "  Commands (6): pull_request, squash, rebase, release, branch, git-find-fork"
      echo "  Skills (3): git-find-fork, git-rewrite-history, gh-assets-branch-mgmt"
      echo "  Agents (0): none"
      echo "  Hooks (0): none"
      ;;
    agentic-review)
      echo "  Commands (5): review, e2e-review, pr-review, full-review, lint-review"
      echo "  Skills (2): dry-run, single-file-uv-scripter"
      echo "  Agents (0): none"
      echo "  Hooks (0): none"
      ;;
    agentic-tools)
      echo "  Commands (9): browser, gsuite, video-query, adr, milestone, ..."
      echo "  Skills (2): gsuite, playwright-cli"
      echo "  Agents (0): none"
      echo "  Hooks (1): gsuite-public-asset-guard"
      ;;
  esac
  echo ""
done

echo "=== PASS/FAIL checklist ==="
echo "[ ] SC-1: claude plugin validate passes"
echo "[ ] SC-3a: marketplace added successfully"
for p in "${PLUGINS[@]}"; do
  echo "[ ] SC-3b: $p installed successfully"
  echo "[ ] $p: commands visible in /help"
  echo "[ ] $p: skills discoverable"
  echo "[ ] $p: agents visible (if applicable)"
done
