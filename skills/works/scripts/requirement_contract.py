#!/usr/bin/env python3
"""Create and validate the autonomous requirement-to-verification contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
import re


ERROR = "E302_INVALID_REQUIREMENT_CONTRACT"
REQ_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
TEST_SELECTOR = re.compile(r"[^#\s,]+#[^#\s,]+")


def executable_name(value: str) -> str:
    return (PureWindowsPath(value).name if "\\" in value else Path(value).name).lower()


def natural_id_key(value: str) -> tuple[tuple[int, object], ...]:
    return tuple((0, int(part)) if part.isdigit() else (1, part.lower())
                 for part in re.split(r"(\d+)", value) if part)


def focused_maven_command(command: list[str]) -> bool:
    if not command or executable_name(command[0]) not in {"mvn", "mvnw", "mvnw.cmd"}:
        return False
    if command[-1] != "test" or command.count("test") != 1:
        return False
    if any(goal in command for goal in ("verify", "package", "install")):
        return False
    if command.count("-pl") != 1:
        return False
    module_index = command.index("-pl") + 1
    if module_index >= len(command):
        return False
    module = command[module_index]
    if not module or module.startswith("-") or "," in module:
        return False
    selectors = [part.removeprefix("-Dtest=") for part in command if part.startswith("-Dtest=")]
    return len(selectors) == 1 and TEST_SELECTOR.fullmatch(selectors[0]) is not None


def template(requirement: Path) -> dict:
    return {
        "version": 1,
        "requirement": str(requirement.resolve()),
        "requirements": [],
        "acceptance_commands": [],
    }


def validate(data: object, requirement: Path) -> list[str]:
    if not isinstance(data, dict):
        return ["contract must be an object"]
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    if Path(str(data.get("requirement", ""))).resolve() != requirement.resolve():
        errors.append("requirement must match the discovered requirement document")
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
        criteria = row.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or any(
            not isinstance(item, str) or not item.strip() for item in criteria
        ):
            errors.append(f"{prefix}.acceptance_criteria must contain executable behaviors")
    if len(ids) != len(set(ids)):
        errors.append("requirement IDs must be unique and ordered")
    elif ids != sorted(ids, key=natural_id_key):
        errors.append("requirement IDs must be ordered in natural order")

    commands = data.get("acceptance_commands")
    if not isinstance(commands, list) or not commands:
        errors.append("acceptance_commands must be a non-empty array")
        commands = []
    command_ids: list[str] = []
    covered: set[str] = set()
    maven_covered: set[str] = set()
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
            if not focused_maven_command(command):
                errors.append(f"{prefix}.command must target one Maven module and exact testcase")
            elif "-DskipTests=false" not in command or "-Dmaven.test.skip=false" not in command:
                errors.append(f"{prefix}.command must explicitly enable Maven tests")
            else:
                maven_covered.update(req for req in coverage if req in ids)
    if len(command_ids) != len(set(command_ids)):
        errors.append("acceptance command IDs must be unique")
    missing = [req for req in ids if req not in covered]
    if missing:
        errors.append(f"requirements missing acceptance command coverage: {missing!r}")
    missing_maven = [req for req in ids if req not in maven_covered]
    if missing_maven:
        errors.append(f"requirements missing Maven test/verify/package coverage: {missing_maven!r}")
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
    errors = validate(data, requirement)
    if errors:
        print(json.dumps({"ok": False, "error": ERROR, "violations": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "requirements": [row["id"] for row in data["requirements"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
