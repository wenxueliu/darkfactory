#!/usr/bin/env python3
"""kb — Unified CLI entry for Harness KB scripts.

This script is a thin wrapper that dispatches to the existing
kb-*.py scripts in the same directory. It exists for:
1. Discoverability: `python kb.py help` shows all subcommands
2. Stable surface: future internal refactors of individual scripts
   don't break the user-facing CLI
3. CI friendliness: one entry point to lint/check/install

Usage:
    python kb.py <subcommand> [args...]

Subcommands (each maps to a kb-*.py script):
    health        Run kb-health.py — generate KB health report
    search        Run kb-search.py — full-text search across KB
    freshness     Run kb-freshness.py — detect/manage stale entries
    index         Run kb-index.py — rebuild, validate, detect orphans
    log           Run kb-log.py — create Pattern/Decision/Lesson/API entries
    merge         Run kb-merge.py — deduplicate similar entries
    distill       Run kb-distill.py — lossless LLM-optimized compression
    service-discovery  Run kb-service-discovery.py — scan services/, generate entries

Examples:
    python kb.py health --format html --output kb-report.html
    python kb.py search "user authentication" --limit 5
    python kb.py freshness --list-stale
    python kb.py index --check-staleness
    python kb.py log --stdin < entry.md

Exit code:
    Propagates the underlying script's exit code.
    If the subcommand is unknown, exits 1.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

SUBCOMMANDS = {
    "health": "kb-health.py",
    "search": "kb-search.py",
    "freshness": "kb-freshness.py",
    "index": "kb-index.py",
    "log": "kb-log.py",
    "merge": "kb-merge.py",
    "distill": "kb-distill.py",
    "service-discovery": "kb-service-discovery.py",
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        print()
        print("Available subcommands:")
        for sub, script in SUBCOMMANDS.items():
            script_path = SCRIPT_DIR / script
            status = "OK" if script_path.is_file() else "MISSING"
            print(f"  {sub:<22} → {script} [{status}]")
        return 0

    sub = sys.argv[1]
    if sub not in SUBCOMMANDS:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        print(f"Available: {', '.join(SUBCOMMANDS)}", file=sys.stderr)
        return 1

    target = SCRIPT_DIR / SUBCOMMANDS[sub]
    if not target.is_file():
        print(f"Error: {target} not found.", file=sys.stderr)
        return 1

    # Pass remaining args to the sub-script
    args = [sys.executable, str(target), *sys.argv[2:]]
    try:
        result = subprocess.run(args)
        return result.returncode
    except FileNotFoundError:
        print(f"Error: {sys.executable} not found.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
