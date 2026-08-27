#!/usr/bin/env python3
"""Block new host tools while Works feedback or hard control is pending."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hook_common import find_active_works_root, load_state, read_input, works_feedback


CONTROL_COMMAND = re.compile(
    r"(?:^|[/\\])works\.py(?:\s|.*\s)(?:next|route|feedback-respond|feedback-list|status|resume|pause|feedback)(?:\s|$)"
)


def is_control_tool(payload: dict) -> bool:
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return False
    command = tool_input.get("command", tool_input.get("cmd", ""))
    return isinstance(command, str) and CONTROL_COMMAND.search(command) is not None


def main() -> int:
    payload = read_input()
    cwd = payload.get("cwd", "")
    if not isinstance(cwd, str) or not cwd or is_control_tool(payload):
        return 0
    root = find_active_works_root(Path(cwd))
    if root is None:
        return 0
    state = load_state(root / ".works" / "state.json")
    pending = [row for row in works_feedback(root)
               if row.get("status") in ("delivered", "observed", "acknowledged")]
    blocked = bool(pending or state.get("active_question")
                   or state.get("awaiting_route")
                   or state.get("execution_state") in (
                       "interrupt_requested", "waiting_for_human", "paused",
                   ))
    if not blocked:
        return 0
    ids = ", ".join(str(row.get("id")) for row in pending[:5]) or "none"
    reason = (
        "Works blocked this tool at a feedback boundary. "
        f"execution_state={state.get('execution_state')}, pending={ids}. "
        "Run `works next` first. Only Works status/next/route/feedback response/pause/resume "
        "control commands may run until the returned action is resolved."
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
