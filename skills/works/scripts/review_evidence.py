#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from works_core.common import atomic_json


def requirement_ids(contract: Path) -> list[str]:
    data = json.loads(contract.read_text(encoding="utf-8"))
    return [row["id"] for row in data.get("requirements", [])]


def template(kind: str, reqs: list[str]) -> dict:
    rows = [{"id": req, "status": "", "finding": ""} for req in reqs]
    value = {"version": 1, "type": kind, "result": "", "requirements": rows, "extra": []}
    if kind == "contract":
        value.update({"missing": [], "ambiguous": [], "invalid_acceptance": []})
    else:
        for row in rows:
            row.update({"implementation": [], "tests": []})
    return value


def validate_payload(data: object, kind: str, reqs: list[str]) -> list[str]:
    """Validate a verifier payload before it is allowed to replace the template."""
    if not isinstance(data, dict):
        return ["review must be a JSON object"]
    top_fields = {"version", "type", "result", "requirements", "extra"}
    issue_fields = {"missing", "ambiguous", "invalid_acceptance"} if kind == "contract" else set()
    errors: list[str] = []
    if set(data) != top_fields | issue_fields:
        errors.append("review payload fields must exactly match the initialized template")
    if data.get("version") != 1 or data.get("type") != kind:
        errors.append("review version/type is invalid")
    if data.get("result") not in {"PASS", "FAIL"}:
        errors.append("review result must be PASS or FAIL")
    rows = data.get("requirements")
    expected_row_fields = {"id", "status", "finding"}
    if kind == "implementation":
        expected_row_fields |= {"implementation", "tests"}
    if not isinstance(rows, list) or [row.get("id") for row in rows if isinstance(row, dict)] != reqs:
        errors.append("review requirements must exactly match the requirement contract")
        rows = []
    for row in rows:
        if set(row) != expected_row_fields:
            errors.append(f"{row.get('id', '?')}: fields must exactly match the initialized template")
        if row.get("status") not in {"PASS", "FAIL"}:
            errors.append(f"{row.get('id', '?')}: status must be PASS or FAIL")
        if not isinstance(row.get("finding"), str):
            errors.append(f"{row.get('id', '?')}: finding must be a string")
        elif row.get("status") == "FAIL" and not row["finding"].strip():
            errors.append(f"{row.get('id', '?')}: FAIL requires a finding")
        if kind == "implementation":
            for field in ("implementation", "tests"):
                if not isinstance(row.get(field), list):
                    errors.append(f"{row.get('id', '?')}: {field} must be an array")
    for field in {"extra"} | issue_fields:
        values = data.get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"{field} must be an array of non-empty strings")
    if data.get("result") == "PASS" and any(row.get("status") != "PASS" for row in rows):
        errors.append("PASS result requires every requirement status to be PASS")
    return errors


def _validate_locations(value: object, field: str, req: str, project_root: Path | None) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{req}: {field} evidence is required"]
    if project_root is None:
        return [f"{req}: project root is required to validate {field} evidence"]

    errors: list[str] = []
    root = project_root.resolve()
    for index, item in enumerate(value):
        label = f"{req}: {field}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object with path, line, symbol, and reason")
            continue
        path_value = item.get("path")
        line = item.get("line")
        for key in ("symbol", "reason"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{label}.{key} must be a non-empty string")
        if not isinstance(path_value, str) or not path_value.strip():
            errors.append(f"{label}.path must be a non-empty project-relative path")
            continue
        relative = Path(path_value)
        if relative.is_absolute():
            errors.append(f"{label}.path must be project-relative")
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"{label}.path escapes the project root")
            continue
        if not candidate.is_file():
            errors.append(f"{label}.path does not exist as a file: {path_value}")
            continue
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            errors.append(f"{label}.line must be a positive integer")
            continue
        try:
            line_count = sum(1 for _ in candidate.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"{label}.path cannot be read: {exc}")
            continue
        if line > line_count:
            errors.append(f"{label}.line {line} exceeds file length {line_count}")
    return errors


def validate(data: object, kind: str, reqs: list[str], project_root: Path | None = None) -> list[str]:
    errors = validate_payload(data, kind, reqs)
    if not isinstance(data, dict):
        return errors
    rows = data.get("requirements")
    if (not isinstance(rows, list)
            or [row.get("id") for row in rows if isinstance(row, dict)] != reqs):
        rows = []
    if data.get("result") != "PASS":
        errors.append("review result must be PASS")
    for row in rows:
        if row.get("status") != "PASS":
            errors.append(f"{row.get('id', '?')}: status must be PASS")
        if kind == "implementation":
            req = row.get("id", "?")
            errors.extend(_validate_locations(row.get("implementation"), "implementation", req, project_root))
            errors.extend(_validate_locations(row.get("tests"), "test", req, project_root))
    fields = ["extra"] if kind == "implementation" else ["missing", "extra", "ambiguous", "invalid_acceptance"]
    for field in fields:
        if data.get(field):
            errors.append(f"{field} must be empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "submit", "validate"])
    parser.add_argument("--type", choices=["contract", "implementation"], required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    target = args.output if args.action == "init" else args.file
    if target is None:
        parser.error("init requires --output; validate requires --file")
    if args.action == "init":
        if target.exists():
            raise SystemExit(f"review already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(template(args.type, requirement_ids(args.contract)), ensure_ascii=False, indent=2) + "\n")
        return 0
    if args.action == "submit":
        if args.input is None:
            parser.error("submit requires --input")
        if not target.exists():
            print(f"review template does not exist: {target}")
            return 1
        try:
            data = json.loads(args.input.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"invalid review payload: {exc}")
            return 1
        errors = validate_payload(data, args.type, requirement_ids(args.contract))
        if errors:
            print("\n".join(errors))
            return 1
        atomic_json(target, data)
        return 0
    try:
        data = json.loads(target.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid review file: {exc}")
        return 1
    errors = validate(data, args.type, requirement_ids(args.contract), args.project_root)
    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
