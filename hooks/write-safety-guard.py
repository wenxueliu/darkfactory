#!/usr/bin/env python3
"""Deny writes to existing project files that were not read first."""

from __future__ import annotations

import json
import time
from pathlib import Path

from hook_common import (
    STATE_ROOT,
    detect_project_root,
    load_state,
    patch_has_context,
    read_input,
    resolve_file_path,
    save_state,
    tool_file_paths,
)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main() -> int:
    payload = read_input()
    session_id = payload.get("session_id", "")
    file_paths = tool_file_paths(payload)
    cwd_value = payload.get("cwd", "")
    cwd = cwd_value if isinstance(cwd_value, str) else ""
    if not isinstance(session_id, str) or not session_id or not file_paths:
        return 0

    project_root = detect_project_root(Path(cwd)) if cwd else None
    if project_root is None:
        return 0

    state_path = STATE_ROOT / "write-safety-guard" / f"{session_id}.json"
    state = load_state(state_path)
    paths = state.get("readPaths", [])
    if not isinstance(paths, list):
        paths = []
    protected: list[tuple[str, Path]] = []
    for file_path in file_paths:
        canonical = resolve_file_path(file_path, cwd)
        if (
            canonical.is_file()
            and ".sisyphus" not in canonical.parts
            and is_within(canonical, project_root)
        ):
            protected.append((file_path, canonical))
    if not protected:
        return 0

    unread = [
        (raw, path)
        for raw, path in protected
        if str(path) not in paths and not patch_has_context(payload, raw)
    ]
    if not unread:
        consumed = {str(path) for _, path in protected}
        paths = [path for path in paths if path not in consumed]
        state["readPaths"] = paths
        state["updatedAt"] = int(time.time())
        save_state(state_path, state)
        return 0

    reason = (
        "Write blocked: existing file(s) "
        f"{', '.join(Path(raw).name for raw, _ in unread)} have not been read in this "
        "session. You MUST read the file first using the Read tool before modifying "
        "it. This is a safety measure to ensure you understand the current content "
        "before making changes."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
