#!/usr/bin/env python3
"""Remove per-session and expired Harness hook state."""

from __future__ import annotations

import json
import time
from pathlib import Path

from hook_common import STATE_ROOT, read_input


MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def cleanup(session_id: str, now: float | None = None) -> None:
    if not session_id or not STATE_ROOT.is_dir():
        return
    cutoff = (time.time() if now is None else now) - MAX_AGE_SECONDS
    for path in STATE_ROOT.glob("*/*.json"):
        try:
            if path.name == f"{session_id}.json" or path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def main() -> int:
    payload = read_input()
    session_id = payload.get("session_id", "")
    cleanup(session_id if isinstance(session_id, str) else "")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": "",
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
