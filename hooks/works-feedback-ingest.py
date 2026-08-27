#!/usr/bin/env python3
"""Persist UserPromptSubmit messages into the nearest active Works inbox."""

from __future__ import annotations

import re
from pathlib import Path

from hook_common import emit_context, find_active_works_root, read_input, write_works_feedback


PAUSE = re.compile(
    r"^(?:请)?(?:立即)?(?:暂停|停止|停下|不要继续|别继续)(?:执行|工作|修改)?[，,。.!！\s]*(?:不要.*)?$",
    re.IGNORECASE,
)
RESUME = re.compile(
    r"^(?:请)?(?:恢复|继续)(?:执行|工作|修改|这个任务)?[。.!！\s]*$|^resume[。.!！\s]*$",
    re.IGNORECASE,
)


def main() -> int:
    payload = read_input()
    prompt = payload.get("prompt", "") or payload.get("user_prompt", "") or ""
    cwd = payload.get("cwd", "")
    if not isinstance(prompt, str) or not prompt.strip() or not isinstance(cwd, str) or not cwd:
        return 0
    root = find_active_works_root(Path(cwd))
    if root is None:
        return 0
    message = prompt.strip()
    action = "pause" if PAUSE.fullmatch(message) else "resume" if RESUME.fullmatch(message) else None
    fields = ({"kind": "control", "action": action, "reason": message}
              if action else {"kind": "message", "message": message})
    item = write_works_feedback(root, {
        **fields,
        "status": "delivered",
        "source": {
            "host_event": "UserPromptSubmit",
            "session_id": payload.get("session_id", ""),
        },
    })
    emit_context(
        "UserPromptSubmit",
        f"[Works Feedback — Harness] 已将本轮消息保存为 {item['id']} "
        f"({item['kind']}{':' + action if action else ''})。在启动任何其他工具前必须执行 "
        "`works next`，并严格处理返回的 interpret_feedback/paused 动作。",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
