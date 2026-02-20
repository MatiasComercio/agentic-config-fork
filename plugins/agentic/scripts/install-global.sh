#!/usr/bin/env bash
set -euo pipefail

# Plugin root: set by Claude Code plugin runtime or derive from script location
: "${CLAUDE_PLUGIN_ROOT:="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

# Source path persistence library
source "${CLAUDE_PLUGIN_ROOT}/scripts/lib/path-persistence.sh"

CLAUDE_USER_DIR="$HOME/.claude"
CLAUDE_COMMANDS_DIR="$CLAUDE_USER_DIR/commands"
CLAUDE_MD="$CLAUDE_USER_DIR/CLAUDE.md"

# Ensure directories exist
mkdir -p "$CLAUDE_COMMANDS_DIR"

# Symlink all agentic commands
for cmd in agentic agentic-setup agentic-migrate agentic-update agentic-status; do
  src="${CLAUDE_PLUGIN_ROOT}/commands/${cmd}.md"
  if [[ -f "$src" ]]; then
    ln -sf "$src" "$CLAUDE_COMMANDS_DIR/${cmd}.md"
    echo "  Linked /${cmd}"
  fi
done

# Append to CLAUDE.md if not already present
MARKER="## Agentic-Config Global"
if ! grep -q "$MARKER" "$CLAUDE_MD" 2>/dev/null; then
  # Use plugin root path
  cat >> "$CLAUDE_MD" << EOF

## Agentic-Config Global
When \`/agentic\` command is triggered, read the appropriate agent definition from:
\`${CLAUDE_PLUGIN_ROOT}/agents/agentic-{action}.md\`

Actions: setup, migrate, update, status, validate, customize

Example: \`/agentic setup\` -> read \`${CLAUDE_PLUGIN_ROOT}/agents/agentic-setup.md\` and follow its instructions.
EOF
  echo "✓ Added agentic-config section to $CLAUDE_MD"
else
  echo "⊘ Agentic-config section already in $CLAUDE_MD"
fi

# Persist plugin root path to all locations
echo ""
echo "Persisting plugin root path to all locations..."
if persist_agentic_path "${CLAUDE_PLUGIN_ROOT}"; then
  echo "Path persisted to ~/.agents/.path, shell profile, and XDG config"
else
  echo "Some persistence locations failed (non-fatal)"
fi

echo ""
echo "Installation complete. Global commands available:"
echo "  /agentic, /agentic-setup, /agentic-migrate, /agentic-update, /agentic-status"
