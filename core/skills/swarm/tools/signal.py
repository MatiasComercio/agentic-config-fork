#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Signal file creation tool for swarm agents.

Creates completion signals that the orchestrator can verify without
reading agent output files directly.

Usage:
    uv run signal.py <signal_path> --path <output_path> --status <success|fail>
    uv run signal.py <signal_path> --path <output_path> --size <bytes> --status success

Examples:
    uv run signal.py .signals/001-research.done --path research/001-topic.md --status success
    uv run signal.py .signals/002-audit.fail --path audits/002-gap.md --status fail --error "timeout"
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create signal file for swarm agent completion"
    )
    parser.add_argument(
        "signal_path",
        help="Path to signal file (e.g., .signals/001-name.done)",
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to output file this signal represents",
    )
    parser.add_argument(
        "--status",
        choices=["success", "fail"],
        required=True,
        help="Completion status",
    )
    parser.add_argument(
        "--size",
        type=int,
        help="Size in bytes (auto-calculated if output file exists)",
    )
    parser.add_argument(
        "--error",
        help="Error message (only for status=fail)",
    )

    args = parser.parse_args()

    signal_path = Path(args.signal_path)
    output_path = Path(args.path)

    # Auto-calculate size if not provided and file exists
    size = args.size
    if size is None and output_path.exists():
        size = output_path.stat().st_size
    elif size is None:
        size = 0

    # Ensure signal directory exists
    signal_path.parent.mkdir(parents=True, exist_ok=True)

    # Build signal content
    lines = [
        f"path: {args.path}",
        f"size: {size}",
        f"status: {args.status}",
    ]

    if args.error:
        lines.append(f"error: {args.error}")

    signal_content = "\n".join(lines) + "\n"

    # Write signal file
    signal_path.write_text(signal_content)

    # Rename to correct extension based on status
    if args.status == "success" and not signal_path.suffix == ".done":
        final_path = signal_path.with_suffix(".done")
        signal_path.rename(final_path)
        signal_path = final_path
    elif args.status == "fail" and not signal_path.suffix == ".fail":
        final_path = signal_path.with_suffix(".fail")
        signal_path.rename(final_path)
        signal_path = final_path

    print(f"Signal created: {signal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
