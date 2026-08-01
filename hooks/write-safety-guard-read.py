#!/usr/bin/env python3
"""Record files read during a session for the write safety guard."""

from __future__ import annotations

import time

from hook_common import (
    STATE_ROOT,
    load_state,
    read_input,
    resolve_file_path,
    save_state,
    tool_file_path,
)


def main() -> int:
    payload = read_input()
    session_id = payload.get("session_id", "")
    file_path = tool_file_path(payload)
    cwd = payload.get("cwd", "")
    if not isinstance(session_id, str) or not session_id or not file_path:
        return 0
    canonical = resolve_file_path(file_path, cwd if isinstance(cwd, str) else "")
    if not canonical.is_file():
        return 0

    state_path = STATE_ROOT / "write-safety-guard" / f"{session_id}.json"
    state = load_state(state_path)
    paths = state.get("readPaths", [])
    if not isinstance(paths, list):
        paths = []
    value = str(canonical)
    paths = [path for path in paths if path != value]
    paths.insert(0, value)
    save_state(state_path, {
        "sessionID": session_id,
        "readPaths": paths[:1024],
        "updatedAt": int(time.time()),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
