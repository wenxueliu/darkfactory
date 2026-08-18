#!/usr/bin/env python3
"""Reject high-confidence entry-layer dependencies on persistence types."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


ENTRY_ANNOTATIONS = {"Controller", "RestController", "WebServlet", "ControllerAdvice"}
ENTRY_NAME = re.compile(r"(?:Controller|Endpoint|Resource|Job|Listener|Consumer|Handler|Scheduler|Command)(?:\.java)?$")
PERSISTENCE_TYPE = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Mapper|Dao|DAO|Repository))\b")
DIRECT_DATA_ACCESS = {
    "JdbcTemplate", "NamedParameterJdbcTemplate", "EntityManager", "SqlSession",
    "DSLContext", "RedisTemplate", "MongoTemplate",
}
TYPE_DECL = re.compile(r"\b(?:class|interface|record|enum)\s+([A-Za-z_$][\w$]*)")
ANNOTATION = re.compile(r"@([A-Za-z_$][\w$]*)")
IGNORED = {".git", ".planning", "target", "build", ".gradle", "node_modules"}


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def java_files(root: Path):
    for path in root.rglob("*.java"):
        if path.is_file() and not any(part in IGNORED for part in path.relative_to(root).parts):
            yield path


def code_only(source: str) -> str:
    """Remove comments and literals so documentation cannot create violations."""
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", " ", source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", "''", source)
    return source


def is_entry(path: Path, source: str) -> bool:
    annotations = set(ANNOTATION.findall(source))
    declared = TYPE_DECL.search(source)
    name = declared.group(1) if declared else path.stem
    return bool(annotations & ENTRY_ANNOTATIONS or ENTRY_NAME.search(name))


def persistence_types(root: Path) -> set[str]:
    found = set(DIRECT_DATA_ACCESS)
    for path in java_files(root):
        source = code_only(path.read_text(errors="replace"))
        declared = TYPE_DECL.search(source)
        if not declared:
            continue
        name = declared.group(1)
        annotations = set(ANNOTATION.findall(source))
        if (
            PERSISTENCE_TYPE.fullmatch(name)
            or annotations & {"Mapper", "Repository"}
            or re.search(r"\b(?:extends|implements)\b[^\{]*(?:BaseMapper|Repository)\s*<", source)
        ):
            found.add(name)
    return found


def violations(root: Path) -> tuple[dict[str, dict], list[dict]]:
    found: dict[str, dict] = {}
    warnings: list[dict] = []
    known_persistence = persistence_types(root)
    for path in java_files(root):
        source = code_only(path.read_text(errors="replace"))
        if not is_entry(path, source):
            continue
        rel = path.relative_to(root).as_posix()
        imports = set(re.findall(r"^import\s+(?:static\s+)?[\w.]+\.([A-Z][\w$]*);", source, re.MULTILINE))
        declared_dependencies = set(re.findall(
            r"\b([A-Z][\w$]*(?:Mapper|Dao|DAO|Repository))\s+[a-z_$][\w$]*\s*(?:[;,)=])",
            source,
        ))
        used = declared_dependencies | (imports & known_persistence)
        direct = {name for name in DIRECT_DATA_ACCESS if re.search(rf"\b{re.escape(name)}\s+[a-z_$]", source)}
        used.update(direct)
        for persistence_type in sorted(used):
            key = f"{rel}|{persistence_type}"
            found[key] = {"file": rel, "persistence_type": persistence_type, "confidence": "high"}
        referenced = set(PERSISTENCE_TYPE.findall(source)) - used
        warnings.extend(
            {"file": rel, "persistence_type": name, "confidence": "low", "reason": "reference_without_dependency_declaration"}
            for name in sorted(referenced)
        )
    return found, warnings


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def cmd_init(args: argparse.Namespace) -> int:
    root, state = Path(args.project_root).resolve(), Path(args.state_dir).resolve()
    baseline = state / "service-boundary-baseline.json"
    if baseline.exists():
        raise SystemExit("service boundary baseline already exists")
    current, warnings = violations(root)
    atomic_json(baseline, {"project_root": str(root), "violations": current, "warnings": warnings})
    print(baseline)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    state = Path(args.state_dir).resolve()
    baseline_file = state / "service-boundary-baseline.json"
    baseline = load(baseline_file)
    if not baseline:
        raise SystemExit(f"missing service boundary baseline: {baseline_file}")
    root = Path(baseline["project_root"])
    if args.project_root and Path(args.project_root).resolve() != root.resolve():
        raise SystemExit("--project-root does not match the immutable service boundary baseline")
    before = baseline.get("violations", {})
    current, warnings = violations(root)
    introduced = [current[key] for key in sorted(current.keys() - before.keys())]
    result = {
        "passed": not introduced,
        "introduced": introduced,
        "warnings": warnings,
        "baseline_count": len(before),
        "current_count": len(current),
        "baseline_sha256": hashlib.sha256(baseline_file.read_bytes()).hexdigest(),
    }
    atomic_json(state / "service-boundary-verify.json", result)
    if introduced:
        details = ", ".join(f"{row['file']} -> {row['persistence_type']}" for row in introduced)
        raise SystemExit("new entry-to-persistence dependency forbidden; reuse/extend a Service API: " + details)
    print(state / "service-boundary-verify.json")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project-root", required=True)
    init.add_argument("--state-dir", required=True)
    init.set_defaults(func=cmd_init)
    verify = sub.add_parser("verify")
    verify.add_argument("--state-dir", required=True)
    verify.add_argument("--project-root")
    verify.set_defaults(func=cmd_verify)
    return root


if __name__ == "__main__":
    ns = parser().parse_args()
    raise SystemExit(ns.func(ns))
