#!/usr/bin/env bash
# B-002: Hook Testing from Plugin Cache
# SC-7: Hooks fire correctly from plugin cache via ${CLAUDE_PLUGIN_ROOT}
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Hook inventory ==="
echo "Plugin: agentic"
echo "  hooks/hooks.json:"
echo "    PreToolUse (Write|Edit|NotebookEdit|Bash):"
echo "      - dry-run-guard.py (blocks writes when DRY_RUN env var set)"
echo "      - git-commit-guard.py (blocks commits to main/master)"
echo ""
echo "Plugin: agentic-tools"
echo "  hooks/hooks.json:"
echo "    PreToolUse (Bash):"
echo "      - gsuite-public-asset-guard.py (blocks public sharing of gsuite assets)"
echo ""
echo "Plugin: agentic-mux"
echo "  No plugin-level hooks.json (skill-level hooks only via SKILL.md frontmatter)"
echo ""

echo "=== Test 1: dry-run-guard ==="
echo "Setup: export DRY_RUN=1"
echo "Load: claude --plugin-dir $REPO_ROOT/plugins/agentic"
echo "Action: Try to write a file (should be blocked)"
echo "Expected: Hook blocks the write with dry-run message"
echo ""

echo "=== Test 2: git-commit-guard ==="
echo "Load: claude --plugin-dir $REPO_ROOT/plugins/agentic"
echo "Action: Try 'git commit' on main branch (should be blocked)"
echo "Expected: Hook blocks commit to main/master"
echo ""

echo "=== Test 3: gsuite-public-asset-guard ==="
echo "Load: claude --plugin-dir $REPO_ROOT/plugins/agentic-tools"
echo "Action: Try to share a gsuite asset publicly"
echo "Expected: Hook blocks public sharing"
echo ""

echo "=== Test 4: Plugin cache verification ==="
echo "After installing via marketplace, verify hooks resolve from cache:"
echo "1. Install agentic via marketplace"
echo "2. Check plugin cache: ls ~/.claude/plugins/cache/*/agentic/scripts/hooks/"
echo "3. Verify dry-run-guard.py and git-commit-guard.py exist in cache"
echo "4. Trigger a hook and verify it runs from cache path"
echo ""

echo "=== Test 5: \${CLAUDE_PLUGIN_ROOT} resolution ==="
echo "After install, check that hook command resolves correctly:"
echo "  Expected: \${CLAUDE_PLUGIN_ROOT} -> ~/.claude/plugins/cache/<hash>/agentic/"
echo "  Hook command: uv run --no-project --script \${CLAUDE_PLUGIN_ROOT}/scripts/hooks/dry-run-guard.py"
echo ""

echo "=== PASS/FAIL checklist ==="
echo "[ ] SC-7: dry-run-guard fires from --plugin-dir"
echo "[ ] SC-7: git-commit-guard fires from --plugin-dir"
echo "[ ] SC-7: gsuite-public-asset-guard fires from --plugin-dir"
echo "[ ] SC-7: Hook scripts exist in plugin cache after marketplace install"
echo "[ ] SC-7: \${CLAUDE_PLUGIN_ROOT} resolves to cache dir"
echo "[ ] SC-7: Hooks fire correctly from plugin cache"
