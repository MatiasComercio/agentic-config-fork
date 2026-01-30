#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Session directory creation tool for mux orchestrator.

Generates unique trace ID for distributed tracing across agents.

Creates the standard session directory structure with all required subdirectories.

Usage:
    uv run session.py <topic_slug>
    uv run session.py <topic_slug> --base tmp/mux

Output (stdout):
    SESSION_DIR=tmp/mux/20260129-1500-topic
    TRACE_ID=a1b2c3d4e5f67890
"""

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create mux session directory structure"
    )
    parser.add_argument(
        "topic_slug",
        help="Topic slug for session ID (e.g., 'auth-research')",
    )
    parser.add_argument(
        "--base",
        default="tmp/mux",
        help="Base directory for mux sessions (default: tmp/mux)",
    )
    parser.add_argument(
        "--parent-trace",
        dest="parent_trace",
        help="Parent trace ID for child sessions (propagation)",
    )

    args = parser.parse_args()

    # Generate session ID: YYYYMMDD-HHMM-topic
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    session_id = f"{timestamp}-{args.topic_slug}"
    session_dir = Path(args.base) / session_id

    # Create directory structure
    subdirs = ["research", "audits", "consolidated", "spy", ".signals", ".agents"]
    for subdir in subdirs:
        (session_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Generate or propagate trace ID
    if args.parent_trace:
        # Child session: use parent trace with new span
        trace_id = args.parent_trace
    else:
        # Root session: generate new trace ID (16 hex chars)
        trace_id = uuid.uuid4().hex[:16]

    # Store trace ID in session
    trace_file = session_dir / ".trace"
    trace_file.write_text(f"{trace_id}\n")

    # Output for shell consumption
    print(f"SESSION_DIR={session_dir}")
    print(f"TRACE_ID={trace_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
