#!/usr/bin/env python3
"""Shared helpers for Harness hook entry points."""

from __future__ import annotations

import json
import os
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
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("file_path", tool_input.get("filePath", ""))
    return value if isinstance(value, str) else ""


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
    if os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
        output = {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            }
        }
    else:
        output = {"additionalContext": context}
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
