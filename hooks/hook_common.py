#!/usr/bin/env python3
"""Shared helpers for Harness hook entry points."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


HOOKS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = HOOKS_DIR.parent
STATE_ROOT = HOOKS_DIR / "hook-state"


def read_input() -> dict[str, Any]:
    """Read a hook payload from stdin, treating malformed input as empty."""
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def tool_file_path(payload: dict[str, Any]) -> str:
    paths = tool_file_paths(payload)
    return paths[0] if paths else ""


def tool_file_paths(payload: dict[str, Any]) -> list[str]:
    """Return file targets from Claude file tools or a Codex apply_patch call."""
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return []
    value = tool_input.get(
        "file_path", tool_input.get("filePath", tool_input.get("path", ""))
    )
    if isinstance(value, str) and value:
        return [value]
    if payload.get("tool_name") != "apply_patch":
        return []
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return []
    paths: list[str] = []
    for match in re.finditer(
        r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$", command, re.MULTILINE
    ):
        path = match.group(1)
        if path not in paths:
            paths.append(path)
    return paths


def patch_has_context(payload: dict[str, Any], file_path: str) -> bool:
    """Whether a Codex Update File section proves knowledge of existing content."""
    if payload.get("tool_name") != "apply_patch":
        return False
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return False
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return False
    header = f"*** Update File: {file_path}"
    start = command.find(header)
    if start < 0:
        return False
    body_start = command.find("\n", start)
    if body_start < 0:
        return False
    next_header = command.find("\n*** ", body_start + 1)
    body = command[body_start + 1:next_header if next_header >= 0 else len(command)]
    return any(
        line.startswith(" ") or (line.startswith("-") and not line.startswith("---"))
        for line in body.splitlines()
    )


def resolve_file_path(file_path: str, cwd: str) -> Path:
    path = Path(file_path)
    if not path.is_absolute() and cwd:
        path = Path(cwd) / path
    return path.resolve(strict=False)


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist state so concurrent hooks never see partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def emit_context(event_name: str, context: str) -> None:
    """Emit the platform-specific additional-context envelope."""
    if os.environ.get("COPILOT_CLI"):
        output = {"additionalContext": context}
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            }
        }
    print(json.dumps(output, ensure_ascii=False))


def detect_project_root(start: Path) -> Path | None:
    markers = (".git", "pyproject.toml", "go.mod", "Cargo.toml", "package.json")
    current = start.resolve(strict=False)
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return None
