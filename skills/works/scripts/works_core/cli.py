from __future__ import annotations

import argparse
import json
from pathlib import Path

from .application import Application, WorksError


DEFAULT_WORKFLOW = Path(__file__).resolve().parents[2] / "assets" / "workflows" / "development.json"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="works")
    root.add_argument("--project", default=".")
    commands = root.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    commands.add_parser("status")
    check = commands.add_parser("check")
    check.add_argument("--result", choices=("passed", "failed"))
    check.add_argument("--evidence")
    check.add_argument("command", nargs=argparse.REMAINDER)
    return root


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_workflow(path: str) -> dict:
    try:
        return json.loads(Path(path).resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorksError("E102_INVALID_WORKFLOW", f"cannot load workflow: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    app = Application()
    project = Path(args.project).resolve()
    try:
        if args.action == "init":
            result = app.init(project, load_workflow(args.workflow))
        elif args.action == "status":
            result = app.status(project)
        else:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if command:
                if args.result or args.evidence:
                    raise WorksError("E203_CHECK_REQUIRED",
                                     "use either a command or --result/--evidence")
                result = app.check_command(project, command)
            else:
                if args.result is None or not args.evidence:
                    raise WorksError("E203_CHECK_REQUIRED",
                                     "check requires a command, or --result with --evidence")
                result = app.check(project, args.result == "passed", args.evidence)
        emit(result)
        return 0
    except WorksError as exc:
        emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
