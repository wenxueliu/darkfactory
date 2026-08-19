#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def validate(data: object, kind: str, reqs: list[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["review must be a JSON object"]
    if data.get("version") != 1 or data.get("type") != kind:
        errors.append("review version/type is invalid")
    rows = data.get("requirements")
    if not isinstance(rows, list) or [row.get("id") for row in rows if isinstance(row, dict)] != reqs:
        errors.append("review requirements must exactly match the requirement contract")
        rows = []
    if data.get("result") != "PASS":
        errors.append("review result must be PASS")
    for row in rows:
        if row.get("status") != "PASS":
            errors.append(f"{row.get('id', '?')}: status must be PASS")
        if kind == "implementation":
            if not row.get("implementation"):
                errors.append(f"{row.get('id', '?')}: implementation evidence is required")
            if not row.get("tests"):
                errors.append(f"{row.get('id', '?')}: test evidence is required")
    fields = ["extra"] if kind == "implementation" else ["missing", "extra", "ambiguous", "invalid_acceptance"]
    for field in fields:
        if data.get(field):
            errors.append(f"{field} must be empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "validate"])
    parser.add_argument("--type", choices=["contract", "implementation"], required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--contract", type=Path, required=True)
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
    try:
        data = json.loads(target.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid review file: {exc}")
        return 1
    errors = validate(data, args.type, requirement_ids(args.contract))
    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
