"""Shared file-I/O, hashing and cross-platform exec helpers for the works skill."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from collections.abc import Iterable

IGNORED_DIRS = {".git", ".planning", "target", "build", ".gradle", "node_modules"}


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def windows_command(command: list[str]) -> list[str]:
    """Wrap a .cmd/.bat argv[0] for CreateProcess on Windows; identity elsewhere."""
    if os.name == "nt" and command and command[0].lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", *command]
    return command


def branch_token(task_id: str) -> str:
    """Windows-safe filesystem token for a task id.

    Task ids are validated against ``[A-Za-z0-9][A-Za-z0-9._:-]{0,127}``, so in
    practice only ``:`` is ever replaced. Kept ASCII-only so the result is
    portable across OSes and case-insensitive filesystems.
    """
    return re.sub(r"[^A-Za-z0-9._-]", "-", task_id)


def result_filename(task_id: str) -> str:
    """Cross-platform evidence filename for a task id (token + short sha256)."""
    digest = hashlib.sha256(task_id.encode()).hexdigest()[:8]
    return f"{branch_token(task_id)}-{digest}.json"


def ordered_task_ids(task_ids: Iterable[str]) -> list[str]:
    """Stable apply/merge order for a wave's task ids.

    The controller applies Subagent patches and records merge commits in this
    exact order, so ``verify_wave`` must use the same order. Python's ``sorted``
    over ASCII task ids is codepoint order and therefore identical on every OS.
    """
    return sorted(task_ids)


def maven_modules(project: Path) -> list[str]:
    """Return project-relative Maven module directories available to plans."""
    modules: list[str] = []
    for directory, dirnames, filenames in os.walk(project):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        if "pom.xml" not in filenames:
            continue
        relative = Path(directory).resolve().relative_to(project.resolve()).as_posix()
        modules.append(relative or ".")
    return sorted(set(modules))
