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
    for name in ("doctor", "init", "status", "recover"):
        sub.add_parser(name)
    for name in ("preflight", "contract-init", "contract-check", "implement", "test", "finalize",
                 "rework", "reopen", "note"):
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
        elif args.action == "recover":
            result = app.recover(project)
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
