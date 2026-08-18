from __future__ import annotations

import argparse
import json
from pathlib import Path

from .application import Application, WorksError


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="works")
    root.add_argument("--project", default=".")
    sub = root.add_subparsers(dest="action", required=True)
    for name in ("doctor", "init", "status"):
        sub.add_parser(name)
    reqs = sub.add_parser("set-reqs")
    reqs.add_argument("--req", action="append", required=True)
    for name in ("tdd-init", "probe", "impact-init", "impact-check", "red", "green", "verify", "accept"):
        command = sub.add_parser(name)
        command.add_argument("arguments", nargs=argparse.REMAINDER)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    app = Application(Path(__file__).resolve().parents[1])
    project = Path(args.project).resolve()
    try:
        if args.action == "doctor":
            result = app.doctor(project)
        elif args.action == "init":
            result = app.init(project)
        elif args.action == "status":
            result = app.status(project)
        elif args.action == "set-reqs":
            result = app.set_requirements(project, args.req)
        else:
            raw = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            result = app.run(project, args.action, raw)
        emit(result)
        return 0
    except WorksError as exc:
        emit({"ok": False, "error": exc.code, "message": str(exc), "evidence": exc.evidence})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
