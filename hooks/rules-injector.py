#!/usr/bin/env python3
"""Inject nearby project instructions after file access."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import time
from pathlib import Path
from typing import Any

from hook_common import (
    STATE_ROOT,
    emit_context,
    load_state,
    read_input,
    resolve_file_path,
    save_state,
    tool_file_path,
)


ROOT_MARKERS = (
    ".git", "package.json", "pyproject.toml", "go.mod", "Cargo.toml",
    "pom.xml", "Makefile", "CMakeLists.txt",
)
RULE_NAMES = ("AGENTS.md", "CLAUDE.md")
RULE_DIRS = (".claude/rules", ".cursor/rules", ".github/instructions")


def find_project_root(path: Path) -> Path:
    for candidate in (path.parent, *path.parent.parents):
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate
    return path.parent


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    metadata: dict[str, Any] = {}
    current_key = ""
    for line in content[3:end].strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ":" in stripped and not line[:1].isspace():
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            metadata[current_key] = value.strip().strip('"').strip("'")
        elif current_key and stripped.startswith("- "):
            existing = metadata.get(current_key)
            if not isinstance(existing, list):
                existing = []
                metadata[current_key] = existing
            existing.append(stripped[2:].strip())
    return metadata, content[end + 3:].strip()


def normalize_patterns(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        return [part.strip().strip('"').strip("'") for part in raw.split(",") if part.strip()]
    return []


def matches_globs(file_path: Path, project_root: Path, patterns: list[str]) -> bool:
    try:
        relative = file_path.relative_to(project_root).as_posix()
    except ValueError:
        relative = file_path.as_posix()
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(file_path.name, pattern)
        for pattern in patterns
    )


def discover_rules(target: Path, root: Path, injected_paths: set[str]) -> list[tuple[Path, int]]:
    discovered: list[tuple[Path, int]] = []
    directory = target.parent
    while directory == root or root in directory.parents:
        distance = 0 if directory == root else len(directory.relative_to(root).parts)
        for name in RULE_NAMES:
            rule = directory / name
            if rule.is_file() and str(rule.resolve()) not in injected_paths:
                discovered.append((rule.resolve(), distance))
        for relative_dir in RULE_DIRS:
            rule_dir = directory / relative_dir
            if rule_dir.is_dir():
                for rule in sorted(rule_dir.glob("*.md")):
                    if rule.is_file() and str(rule.resolve()) not in injected_paths:
                        discovered.append((rule.resolve(), distance))
        if directory == root:
            break
        directory = directory.parent
    return sorted(set(discovered), key=lambda item: (item[1], item[0].name))


def build_injection(target: Path, session_id: str) -> str:
    root = find_project_root(target)
    state_path = STATE_ROOT / "rules-injector" / f"{session_id}.json"
    state = load_state(state_path)
    injected_hashes = set(state.get("injectedHashes", []))
    injected_paths = set(state.get("injectedRealPaths", []))
    parts: list[str] = []

    for rule, distance in discover_rules(target, root, injected_paths):
        try:
            content = rule.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(content) > 8000:
            content = content[:8000] + "\n\n... [truncated]"
        metadata, body = parse_frontmatter(content)
        patterns = normalize_patterns(metadata.get("globs", metadata.get("glob", "")))
        patterns.extend(normalize_patterns(metadata.get("paths", "")))
        always = str(metadata.get("alwaysApply", "")).lower() in {"true", "yes", "1"}
        if always:
            reason = "alwaysApply: true"
        elif patterns and matches_globs(target, root, patterns):
            reason = "globs matched"
        elif not patterns and distance == 0:
            reason = "same directory (no globs)"
        else:
            continue
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if digest in injected_hashes:
            continue
        display = body[:4000] + ("\n\n... [truncated]" if len(body) > 4000 else "")
        try:
            relative = rule.relative_to(root).as_posix()
        except ValueError:
            relative = rule.name
        parts.append(f"[Project Rule: {relative}]\n[Match: {reason}]\n\n{display}")
        injected_hashes.add(digest)
        injected_paths.add(str(rule))

    save_state(state_path, {
        **state,
        "sessionID": session_id,
        "injectedHashes": list(injected_hashes)[:256],
        "injectedRealPaths": list(injected_paths)[:256],
        "updatedAt": int(time.time()),
    })
    return "\n\n---\n\n".join(parts)


def main() -> int:
    payload = read_input()
    session_id = payload.get("session_id", "")
    file_path = tool_file_path(payload)
    cwd = payload.get("cwd", "")
    if not isinstance(session_id, str) or not session_id or not file_path:
        return 0
    target = resolve_file_path(file_path, cwd if isinstance(cwd, str) else "")
    if not target.is_file():
        return 0
    injection = build_injection(target, session_id)
    if injection:
        context = (
            "\n[Rules Injection — Harness Multi-Agent System]\n"
            "The following project rules apply to the file you just accessed:\n\n"
            f"{injection}"
        )
        emit_context("PostToolUse", context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
