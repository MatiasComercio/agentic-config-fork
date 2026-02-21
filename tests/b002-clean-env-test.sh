#!/usr/bin/env bash
# B-002: Clean Environment Testing
# SC-6: Zero AGENTS.md, zero symlinks after plugin install
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLEAN_DIR="/tmp/b002-clean-env-test-$$"

echo "=== Setup clean environment ==="
echo "Creating: $CLEAN_DIR"
mkdir -p "$CLEAN_DIR"
cd "$CLEAN_DIR"
git init
echo "# Test" > README.md
git add . && git commit -m "init"

echo ""
echo "=== Pre-install state ==="
echo "Checking no AGENTS.md exists..."
test ! -f AGENTS.md && echo "  PASS: No AGENTS.md" || echo "  FAIL: AGENTS.md exists"
echo "Checking no symlinks..."
SYMLINKS=$(find . -type l 2>/dev/null | wc -l)
echo "  Symlinks found: $SYMLINKS"

echo ""
echo "=== Install plugins ==="
echo "RUN (inside claude session from $CLEAN_DIR):"
echo "  /plugin marketplace add $REPO_ROOT"
echo "  Then install each plugin:"
echo "  claude plugin install agentic@agentic-plugins"
echo "  claude plugin install agentic-spec@agentic-plugins"
echo "  ... (all 6)"
echo ""

echo "=== Post-install verification ==="
echo "RUN:"
echo "  test ! -f $CLEAN_DIR/AGENTS.md && echo 'PASS: No AGENTS.md' || echo 'FAIL: AGENTS.md created'"
echo "  SYMLINKS=\$(find $CLEAN_DIR -type l 2>/dev/null | wc -l)"
echo "  [ \$SYMLINKS -eq 0 ] && echo 'PASS: No symlinks' || echo 'FAIL: \$SYMLINKS symlinks found'"
echo ""

echo "=== PASS/FAIL checklist ==="
echo "[ ] SC-6: No AGENTS.md created after install"
echo "[ ] SC-6: No symlinks created after install"
echo "[ ] SC-6: Plugins functional in clean environment"
