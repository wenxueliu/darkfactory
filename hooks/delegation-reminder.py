#!/usr/bin/env python3
"""Remind orchestrators to delegate after repeated direct tool calls."""

from __future__ import annotations

import time

from hook_common import STATE_ROOT, emit_context, load_state, read_input, save_state


DELEGATION_TOOLS = {"Agent", "Skill"}
COUNTED_TOOLS = {
    "Bash", "Write", "Edit", "Read", "Grep", "Glob", "Task", "TodoWrite",
    "WebFetch", "WebSearch",
}


def reminder(count: int) -> str:
    return (
        f"\n[Delegation Reminder — Harness] {count} direct tool calls without "
        "Agent/Skill delegation.\n\nQuick routing guide:\n"
        "- Search/Read code: Agent(subagent_type=sw-codebase-explorer) [internal] / "
        "sw-external-researcher [external]\n"
        "- Plan multi-step: Agent(subagent_type=sw-strategic-planner)\n"
        "- Execute a plan: Agent(subagent_type=sw-plan-executor) / "
        "sw-worktree-controller [single task]\n"
        "- Reviews (4-way, mandatory after TDD): sw-reviewer-logic + "
        "sw-reviewer-security + sw-reviewer-performance + sw-reviewer-context\n"
        "- Deep architecture/security: sw-strategic-advisor\n"
        "- Knowledge: sw-knowledge-agent\n"
        "- Tests/integration: sw-integration-tester (newman hard-exec)\n"
        "- Deploy: sw-deployer\n\n"
        "Direct Bash/Read/Write/Edit chains of 3+ are a red flag — delegate instead.\n"
        "If you genuinely need to do this work yourself (Trivial, single file, "
        "<10 lines, no cross-service), add a one-line justification in your final answer."
    )


def main() -> int:
    payload = read_input()
    session_id = payload.get("session_id", "")
    tool_name = payload.get("tool_name", "")
    if not isinstance(session_id, str) or not session_id:
        return 0

    state_path = STATE_ROOT / "delegation-reminder" / f"{session_id}.json"
    state = load_state(state_path)
    if tool_name in DELEGATION_TOOLS:
        save_state(state_path, {
            "sessionID": session_id,
            "hasDelegated": True,
            "reminderShown": False,
            "toolCallCount": 0,
            "updatedAt": int(time.time()),
        })
        return 0
    if tool_name not in COUNTED_TOOLS:
        return 0

    count = int(state.get("toolCallCount", 0)) + 1
    has_delegated = bool(state.get("hasDelegated", False))
    shown = bool(state.get("reminderShown", False))
    should_remind = count >= 3 and not has_delegated and not shown
    save_state(state_path, {
        "sessionID": session_id,
        "hasDelegated": has_delegated,
        "reminderShown": shown or should_remind,
        "toolCallCount": count,
        "updatedAt": int(time.time()),
    })
    if should_remind:
        emit_context("PostToolUse", reminder(count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
