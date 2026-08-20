"""Shared file-I/O, hashing and cross-platform exec helpers for the works skill."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from collections.abc import Mapping

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


def windows_command(command: list[str], platform: str | None = None,
                    env: Mapping[str, str] | None = None) -> list[str] | str:
    """Build a safe CreateProcess argv for Windows batch files."""
    platform = platform or os.name
    env = os.environ if env is None else env
    if platform == "nt" and command and command[0].lower().endswith((".cmd", ".bat")):
        comspec = env.get("COMSPEC") or env.get("ComSpec") or "cmd.exe"
        # cmd /s strips the outer quote pair. Quote every inner argument so Maven
        # properties such as -Dmaven.test.skip=false survive batch/cmd parsing as
        # one argument even when the caller itself was launched from PowerShell.
        command_line = " ".join(f'"{part.replace(chr(34), chr(34) * 2)}"'
                                for part in command)
        launcher = subprocess.list2cmdline([comspec, "/d", "/s", "/c"])
        return f'{launcher} "{command_line}"'
    return command
