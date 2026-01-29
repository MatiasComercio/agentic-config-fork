#!/usr/bin/env bash
# Bounded summary extraction from swarm output files
# Returns TOC + Executive Summary only, hard capped at specified bytes
#
# Expected file structure:
#   # Title
#   ## Table of Contents
#   ...
#   ## Executive Summary
#   ...
#   ---
#   ## Section 1 (not extracted)

set -euo pipefail

usage() {
    echo "Usage: extract-summary.sh <file> [max_bytes]"
    echo "  file:      Path to markdown file with TOC + Executive Summary"
    echo "  max_bytes: Maximum output size (default: 1024)"
    echo ""
    echo "Extracts content up to first '---' separator (Title + TOC + Executive Summary)"
    exit 1
}

[[ $# -lt 1 ]] && usage
file="$1"
max_bytes="${2:-1024}"

[[ ! -f "$file" ]] && { echo "ERROR: File not found: $file" >&2; exit 1; }

# Strategy 1: Extract up to first --- separator (preferred)
if grep -q "^---$" "$file"; then
    sed -n '1,/^---$/p' "$file" | head -c "$max_bytes"
    exit 0
fi

# Strategy 2: Extract up to first ## heading after Executive Summary
# This handles files without --- separator
if grep -q "^## Executive Summary" "$file"; then
    # Find line number of Executive Summary
    exec_line=$(grep -n "^## Executive Summary" "$file" | head -1 | cut -d: -f1)
    # Find next ## heading after Executive Summary
    next_section=$(tail -n +"$((exec_line + 1))" "$file" | grep -n "^## " | head -1 | cut -d: -f1)
    if [[ -n "$next_section" ]]; then
        # Extract from start to line before next section
        end_line=$((exec_line + next_section - 1))
        head -n "$end_line" "$file" | head -c "$max_bytes"
        exit 0
    fi
fi

# Strategy 3: Fallback - extract first 40 lines (enough for TOC + Summary)
head -40 "$file" | head -c "$max_bytes"
