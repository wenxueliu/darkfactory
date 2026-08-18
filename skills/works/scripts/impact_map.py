#!/usr/bin/env python3
"""Create and validate the machine-readable brownfield impact map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ERROR = "E301_INVALID_IMPACT_MAP"
REQUIRED = ("id", "behavior", "entrypoints", "service_apis", "persistence", "test_seams", "risks")


def template(reqs: list[str]) -> dict:
    return {
        "version": 1,
        "requirements": [
            {
                "id": req,
                "behavior": "",
                "entrypoints": [],
                "service_apis": [],
                "persistence": [],
                "callers": [],
                "config_data_impact": [],
                "test_seams": [],
                "risks": [],
                "architecture_exception": None,
            }
            for req in reqs
        ],
    }


def evidence_path(project: Path, value: str) -> bool:
    path_value = value.rsplit(":", 1)[0] if re.search(r":\d+$", value) else value
    try:
        return (project / path_value).resolve().is_relative_to(project) and (project / path_value).exists()
    except (OSError, ValueError):
        return False


def validate(data: dict, project: Path, expected_reqs: list[str]) -> list[str]:
    errors: list[str] = []
    rows = data.get("requirements")
    if data.get("version") != 1 or not isinstance(rows, list):
        return ["version must be 1 and requirements must be an array"]
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if ids != expected_reqs:
        errors.append(f"requirement order {ids!r} does not match {expected_reqs!r}")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"requirements[{index}] is not an object")
            continue
        prefix = f"requirements[{index}]"
        for field in REQUIRED:
            if field not in row or row[field] in (None, "", []):
                errors.append(f"{prefix}.{field} is required")
        for field in ("entrypoints", "service_apis", "persistence", "callers", "test_seams"):
            values = row.get(field, [])
            if not isinstance(values, list):
                errors.append(f"{prefix}.{field} must be an array")
                continue
            for value in values:
                if not isinstance(value, str) or not evidence_path(project, value):
                    errors.append(f"{prefix}.{field} has missing evidence path: {value!r}")
        if not row.get("service_apis"):
            exception = row.get("architecture_exception")
            if not isinstance(exception, dict) or not all(exception.get(key) for key in ("type", "evidence", "reason")):
                errors.append(f"{prefix} needs service_apis or a typed architecture_exception")
            elif not evidence_path(project, exception["evidence"]):
                errors.append(f"{prefix}.architecture_exception.evidence does not exist")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--output", required=True)
    init.add_argument("--req", action="append", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--file", required=True)
    check.add_argument("--project-root", required=True)
    check.add_argument("--req", action="append", required=True)
    args = parser.parse_args()
    if args.action == "init":
        output = Path(args.output)
        if output.exists():
            raise SystemExit(f"{ERROR}: refusing to overwrite {output}")
        output.write_text(json.dumps(template(args.req), ensure_ascii=False, indent=2) + "\n")
        print(output)
        return 0
    path = Path(args.file)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{ERROR}: {exc}")
    errors = validate(data, Path(args.project_root).resolve(), args.req)
    if errors:
        print(json.dumps({"ok": False, "error": ERROR, "violations": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "requirements": args.req}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
