#!/usr/bin/env python3
"""session-end-check — SessionEnd hook for Harness multiagents.

Event: SessionEnd
Purpose: Detect leftover work at session end and inject a warning context.
         - in_progress tasks in _context/memory/sw-shared/tasks.yaml
         - uncommitted worktrees under .worktree/
         - unfinished sw-shared sub-agents or phase transitions

This hook is INTENTIONALLY SOFT (additionalContext, not deny):
- Denying session end is hostile UX; the user is leaving
- A warning is enough: the next session can pick up where this left off
- The HARD gate for unfinished work is in:
  * ideation-gate.py (PreToolUse, blocks code-writing if ideation not done)
  * completion-gate.md (workflow check, not a hook)

Detection logic:
1. Walk _context/memory/sw-shared/tasks.yaml → count in_progress
2. Walk .worktree/ → count worktree directories
3. If any leftover work → emit warning via additionalContext
4. Otherwise: exit 0 silently
"""

import json
import os
import re
import sys
from pathlib import Path

# Configurable: path patterns to scan
TASKS_FILE_CANDIDATES = [
    "_context/memory/sw-shared/tasks.yaml",
    "_context/memory/sw-shared/tasks.json",
]
WORKTREE_DIR_CANDIDATES = [".worktree", "worktrees"]


def detect_project_root(start_dir: str) -> str:
    markers = {".git", "_context", "pyproject.toml", "go.mod", "Cargo.toml", "package.json"}
    d = Path(start_dir).resolve()
    for _ in range(8):
        for marker in markers:
            if (d / marker).exists():
                return str(d)
        parent = d.parent
        if parent == d:
            break
        d = parent
    return ""


def scan_in_progress_tasks(project_root: str) -> list[dict]:
    """Return list of in_progress task entries with id, status, title."""
    for rel in TASKS_FILE_CANDIDATES:
        path = os.path.join(project_root, rel)
        if not os.path.isfile(path):
            continue
        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue

        # Try YAML first
        try:
            import yaml
            data = yaml.safe_load(content) or {}
            tasks = data.get("tasks", data) if isinstance(data, dict) else data
            if not isinstance(tasks, list):
                continue
            result = []
            for t in tasks:
                if isinstance(t, dict) and t.get("status") == "in_progress":
                    result.append({
                        "id": t.get("id") or t.get("task_id") or "<unknown>",
                        "title": t.get("title") or t.get("name") or "",
                    })
            return result
        except ImportError:
            # PyYAML missing — fall back to simple regex scan
            pass
        except Exception:
            continue

        # Regex fallback: find lines with status: in_progress and adjacent id:
        result = []
        for m in re.finditer(
            r"-\s+id:\s*(\S+).*?status:\s*in_progress",
            content,
            re.DOTALL,
        ):
            result.append({"id": m.group(1), "title": ""})
        if result:
            return result
    return []


def scan_worktrees(project_root: str) -> list[dict]:
    """Return list of worktree directories that have uncommitted changes."""
    result = []
    for rel in WORKTREE_DIR_CANDIDATES:
        base = os.path.join(project_root, rel)
        if not os.path.isdir(base):
            continue
        try:
            for entry in sorted(os.listdir(base)):
                wt_path = os.path.join(base, entry)
                if not os.path.isdir(wt_path):
                    continue
                # Check for uncommitted changes
                git_dir = os.path.join(wt_path, ".git")
                if not os.path.exists(git_dir):
                    # May be a file (worktree pointer)
                    continue
                try:
                    proc = __import__("subprocess").run(
                        ["git", "-C", wt_path, "status", "--porcelain"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if proc.returncode == 0 and proc.stdout.strip():
                        result.append({
                            "name": entry,
                            "path": wt_path,
                            "dirty_files": len(proc.stdout.strip().splitlines()),
                        })
                except Exception:
                    pass
        except OSError:
            pass
    return result


def build_warning(in_progress: list[dict], worktrees: list[dict]) -> str:
    parts = ["[Session End — Harness] Leftover state detected:"]
    if in_progress:
        ids = ", ".join(t["id"] for t in in_progress[:10])
        suffix = f" (showing 10 of {len(in_progress)})" if len(in_progress) > 10 else ""
        parts.append(f"  • {len(in_progress)} in_progress task(s): {ids}{suffix}")
    if worktrees:
        names = ", ".join(f"{w['name']}({w['dirty_files']} files)" for w in worktrees[:5])
        suffix = f" (showing 5 of {len(worktrees)})" if len(worktrees) > 5 else ""
        parts.append(f"  • {len(worktrees)} worktree(s) with uncommitted changes: {names}{suffix}")

    parts.append(
        "Recommendation: Either complete the work in the next session, or "
        "use sw-finishing-branch to merge/discard. If the session was interrupted "
        "intentionally, no action needed."
    )
    return "\n".join(parts)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    cwd = input_data.get("cwd", "")
    project_root = detect_project_root(cwd)
    if not project_root:
        sys.exit(0)

    in_progress = scan_in_progress_tasks(project_root)
    worktrees = scan_worktrees(project_root)

    if not in_progress and not worktrees:
        sys.exit(0)

    warning = build_warning(in_progress, worktrees)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionEnd",
            "additionalContext": warning,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
