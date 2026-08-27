#!/usr/bin/env python3
"""Surface Works state again after every host tool boundary."""

from __future__ import annotations

from pathlib import Path

from hook_common import emit_context, find_active_works_root, load_state, read_input, works_feedback


def main() -> int:
    payload = read_input()
    cwd = payload.get("cwd", "")
    if not isinstance(cwd, str) or not cwd:
        return 0
    root = find_active_works_root(Path(cwd))
    if root is None:
        return 0
    state = load_state(root / ".works" / "state.json")
    pending = [row for row in works_feedback(root)
               if row.get("status") in ("delivered", "observed", "acknowledged")]
    if pending:
        identifiers = ", ".join(str(row.get("id")) for row in pending[:5])
        emit_context(
            "PostToolUse",
            f"[Works Boundary — Harness] 检测到待处理反馈 {identifiers}。"
            "不要启动下一工具；立即执行 `works next`。",
        )
    elif state.get("execution_state") in ("interrupt_requested", "paused", "waiting_for_human"):
        emit_context(
            "PostToolUse",
            f"[Works Boundary — Harness] execution_state={state.get('execution_state')}，"
            "当前不得启动新业务动作；执行 `works next` 获取控制动作。",
        )
    elif state.get("awaiting_route"):
        emit_context(
            "PostToolUse",
            "[Works Boundary — Harness] 当前 check 已结束，必须执行 `works next` 获取合法路由候选，"
            "再提交 `works route`。",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
