#!/usr/bin/env bash
# B-002: Combination Testing
# SC-5: All 6 plugins load simultaneously without namespace conflicts
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGINS=(agentic agentic-spec agentic-mux agentic-git agentic-review agentic-tools)

echo "=== Load all 6 plugins simultaneously ==="
PLUGIN_DIRS=""
for p in "${PLUGINS[@]}"; do
  PLUGIN_DIRS="$PLUGIN_DIRS --plugin-dir $REPO_ROOT/plugins/$p"
done
echo "RUN: claude $PLUGIN_DIRS"
echo ""

echo "=== Verification checklist ==="
echo "1. /help -- all commands from all 6 plugins visible"
echo "2. Commands are namespaced: /agentic:setup, /agentic-spec:spec, etc."
echo "3. No error messages about duplicate names or conflicts"
echo "4. Skills from all plugins discoverable"
echo "5. Agents from agentic + agentic-spec visible in /agents"
echo ""

echo "=== Cross-plugin workflow test ==="
echo "Test: mux calling spec (cross-plugin dependency)"
echo "RUN (inside session): /mux -- verify it can invoke spec skills"
echo ""

echo "=== Enable/disable test ==="
echo "1. Install all 6 via marketplace"
echo "2. Disable one: claude plugin disable agentic-tools@agentic-plugins"
echo "3. Verify: /help no longer shows agentic-tools commands"
echo "4. Re-enable: claude plugin enable agentic-tools@agentic-plugins"
echo "5. Verify: /help shows agentic-tools commands again"
echo ""

echo "=== PASS/FAIL checklist ==="
echo "[ ] SC-5: All 6 load without errors"
echo "[ ] SC-5: Commands properly namespaced"
echo "[ ] SC-5: No namespace conflicts"
echo "[ ] SC-5: Cross-plugin workflow works"
echo "[ ] SC-5: Enable/disable works"
