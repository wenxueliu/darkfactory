#!/usr/bin/env python3
"""Create and validate the autonomous requirement-to-verification contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ERROR = "E302_INVALID_REQUIREMENT_CONTRACT"
REQ_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
REUSE_KINDS = {"existing_method", "service_api", "persistence", "architecture_exception"}


def _target_errors(value: object, prefix: str, project: Path) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"path", "symbol"}:
        return [f"{prefix} must contain exactly path and symbol"]
    path_value, symbol = value.get("path"), value.get("symbol")
    if not isinstance(path_value, str) or not path_value or Path(path_value).is_absolute():
        return [f"{prefix}.path must be project-relative"]
    candidate = (project / path_value).resolve()
    try:
        candidate.relative_to(project.resolve())
    except ValueError:
        return [f"{prefix}.path escapes the project root"]
    if not candidate.is_file():
        return [f"{prefix}.path does not exist: {path_value}"]
    if not isinstance(symbol, str) or not symbol.strip():
        return [f"{prefix}.symbol is required"]
    if not re.search(rf"\b{re.escape(symbol)}\b", candidate.read_text(encoding="utf-8", errors="replace")):
        return [f"{prefix}.symbol does not exist in {path_value}: {symbol}"]
    return []


def _planned_target_errors(value: object, prefix: str, project: Path) -> list[str]:
    """Validate a future code target without requiring it to exist during contract authoring."""
    if not isinstance(value, dict) or set(value) != {"path", "symbol"}:
        return [f"{prefix} must contain exactly path and symbol"]
    path_value, symbol = value.get("path"), value.get("symbol")
    if not isinstance(path_value, str) or not path_value or Path(path_value).is_absolute():
        return [f"{prefix}.path must be project-relative"]
    try:
        (project / path_value).resolve().relative_to(project.resolve())
    except ValueError:
        return [f"{prefix}.path escapes the project root"]
    if not isinstance(symbol, str) or not symbol.strip():
        return [f"{prefix}.symbol is required"]
    return []


def _implementation_errors(value: object, prefix: str, project: Path) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"entrypoint", "reuse", "test_target"}:
        return [f"{prefix} must contain exactly entrypoint, reuse, and test_target"]
    errors = _planned_target_errors(value.get("entrypoint"), f"{prefix}.entrypoint", project)
    reuse = value.get("reuse")
    if not isinstance(reuse, dict) or set(reuse) != {"kind", "target", "reason", "absence_evidence"}:
        errors.append(f"{prefix}.reuse must contain exactly kind, target, reason, and absence_evidence")
    else:
        kind = reuse.get("kind")
        if kind not in REUSE_KINDS:
            errors.append(f"{prefix}.reuse.kind is invalid")
        errors.extend(_target_errors(reuse.get("target"), f"{prefix}.reuse.target", project))
        if not isinstance(reuse.get("reason"), str) or not reuse["reason"].strip():
            errors.append(f"{prefix}.reuse.reason is required")
        absence = reuse.get("absence_evidence")
        if not isinstance(absence, list):
            errors.append(f"{prefix}.reuse.absence_evidence must be an array")
        elif kind == "persistence":
            scopes = {item.get("scope") for item in absence if isinstance(item, dict)}
            if scopes != {"current_class", "same_layer_service"} or any(
                not isinstance(item, dict)
                or set(item) != {"scope", "evidence", "reason"}
                or not isinstance(item.get("evidence"), str) or not item["evidence"].strip()
                or not isinstance(item.get("reason"), str) or not item["reason"].strip()
                for item in absence
            ):
                errors.append(f"{prefix}.reuse.persistence requires current_class and same_layer_service evidence")
        elif absence:
            errors.append(f"{prefix}.reuse.absence_evidence is only allowed for persistence")
    test_target = value.get("test_target")
    if (not isinstance(test_target, dict) or set(test_target) != {"file", "selector"}
            or not isinstance(test_target.get("file"), str)
            or not test_target["file"].endswith(("Test.java", "Tests.java", "IT.java"))
            or not isinstance(test_target.get("selector"), str)
            or "#" not in test_target["selector"]):
        errors.append(f"{prefix}.test_target must contain a Maven test file and Class#method selector")
    return errors


def template(requirement: Path) -> dict:
    return {
        "version": 1,
        "requirement": str(requirement.resolve()),
        "requirements": [],
        "acceptance_commands": [],
    }


def normalize_project_paths(data: object, project: Path) -> bool:
    """Canonicalize optional project-directory-prefixed paths in a contract in place."""
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        return False
    changed = False
    for row in data["requirements"]:
        implementation = row.get("implementation", {}) if isinstance(row, dict) else {}
        targets = [implementation.get("entrypoint"),
                   implementation.get("reuse", {}).get("target")
                   if isinstance(implementation.get("reuse"), dict) else None,
                   implementation.get("test_target")]
        for target in targets:
            if not isinstance(target, dict) or not isinstance(target.get("path" if "path" in target else "file"), str):
                continue
            key = "path" if "path" in target else "file"
            relative = Path(target[key].replace("\\", "/"))
            if relative.parts[:1] == (project.name,) and len(relative.parts) > 1:
                target[key] = Path(*relative.parts[1:]).as_posix()
                changed = True
    return changed


def validate(data: object, requirement: Path, project_root: Path | None = None) -> list[str]:
    if not isinstance(data, dict):
        return ["contract must be an object"]
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    if Path(str(data.get("requirement", ""))).resolve() != requirement.resolve():
        errors.append("requirement must match the discovered requirement document")
    project = (project_root or requirement.resolve().parent).resolve()
    rows = data.get("requirements")
    if not isinstance(rows, list) or not rows:
        errors.append("requirements must be a non-empty array")
        rows = []
    ids: list[str] = []
    for index, row in enumerate(rows):
        prefix = f"requirements[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        req = row.get("id")
        if not isinstance(req, str) or not REQ_ID.fullmatch(req):
            errors.append(f"{prefix}.id is invalid")
        else:
            ids.append(req)
        if not isinstance(row.get("statement"), str) or not row["statement"].strip():
            errors.append(f"{prefix}.statement is required")
        source = row.get("source")
        if (not isinstance(source, dict) or set(source) != {"heading", "item"}
                or not all(isinstance(source.get(key), str) and source[key].strip()
                           for key in ("heading", "item"))):
            errors.append(f"{prefix}.source must contain non-empty heading and item")
        criteria = row.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or any(
            not isinstance(item, str) or not item.strip() for item in criteria
        ):
            errors.append(f"{prefix}.acceptance_criteria must contain executable behaviors")
        errors.extend(_implementation_errors(row.get("implementation"), f"{prefix}.implementation", project))
    if len(ids) != len(set(ids)):
        errors.append("requirement IDs must be unique and ordered")
    sources = [json.dumps(row.get("source"), ensure_ascii=False, sort_keys=True)
               for row in rows if isinstance(row, dict) and isinstance(row.get("source"), dict)]
    if len(sources) != len(set(sources)):
        errors.append("requirement sources must be unique")

    commands = data.get("acceptance_commands")
    if not isinstance(commands, list) or not commands:
        errors.append("acceptance_commands must be a non-empty array")
        commands = []
    command_ids: list[str] = []
    covered: set[str] = set()
    maven_covered: set[str] = set()
    selectors_by_req: dict[str, set[str]] = {req: set() for req in ids}
    for index, row in enumerate(commands):
        prefix = f"acceptance_commands[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = row.get("id")
        if not isinstance(name, str) or not REQ_ID.fullmatch(name):
            errors.append(f"{prefix}.id is invalid")
        else:
            command_ids.append(name)
        command = row.get("command")
        if not isinstance(command, list) or not command or any(
            not isinstance(part, str) or not part for part in command
        ):
            errors.append(f"{prefix}.command must be a non-empty argv array")
            command = []
        coverage = row.get("covers")
        if not isinstance(coverage, list) or not coverage:
            errors.append(f"{prefix}.covers must be non-empty")
        else:
            unknown = [req for req in coverage if req not in ids]
            if unknown:
                errors.append(f"{prefix}.covers contains unknown IDs: {unknown!r}")
            covered.update(req for req in coverage if req in ids)
            executable = Path(command[0]).name.lower() if command else ""
            lifecycle = {"test", "verify", "package"} & set(command)
            if executable in {"mvn", "mvnw", "mvnw.cmd"} and lifecycle:
                if "-DskipTests=false" not in command or "-Dmaven.test.skip=false" not in command:
                    errors.append(f"{prefix}.command must explicitly enable Maven tests")
                targeted = [part for part in command if part.startswith("-Dtest=")]
                if len(targeted) != 1 or "#" not in targeted[0]:
                    errors.append(f"{prefix}.command must target exactly one implemented behavior with -Dtest=Class#method")
                else:
                    maven_covered.update(req for req in coverage if req in ids)
                    for req in coverage:
                        if req in selectors_by_req:
                            selectors_by_req[req].add(targeted[0].split("=", 1)[1])
    if len(command_ids) != len(set(command_ids)):
        errors.append("acceptance command IDs must be unique")
    missing = [req for req in ids if req not in covered]
    if missing:
        errors.append(f"requirements missing acceptance command coverage: {missing!r}")
    missing_maven = [req for req in ids if req not in maven_covered]
    if missing_maven:
        errors.append(f"requirements missing Maven test/verify/package coverage: {missing_maven!r}")
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in selectors_by_req:
            continue
        planned = row.get("implementation", {}).get("test_target", {}).get("selector")
        if planned and selectors_by_req[row["id"]] != {planned}:
            errors.append(
                f"{row['id']}: implementation.test_target.selector must match its acceptance command"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--output", required=True)
    init.add_argument("--requirement", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--file", required=True)
    check.add_argument("--requirement", required=True)
    check.add_argument("--project-root", required=True)
    args = parser.parse_args()
    path = Path(args.output if args.action == "init" else args.file)
    requirement = Path(args.requirement)
    if args.action == "init":
        if path.exists():
            raise SystemExit(f"{ERROR}: refusing to overwrite {path}")
        path.write_text(json.dumps(template(requirement), ensure_ascii=False, indent=2) + "\n")
        print(path)
        return 0
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{ERROR}: {exc}")
    project = Path(args.project_root)
    normalized = normalize_project_paths(data, project)
    errors = validate(data, requirement, project)
    if errors:
        print(json.dumps({"ok": False, "error": ERROR, "violations": errors}, ensure_ascii=False, indent=2))
        return 2
    if normalized:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ok": True, "requirements": [row["id"] for row in data["requirements"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
