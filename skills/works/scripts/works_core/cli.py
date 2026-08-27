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
    commands.add_parser("next")
    feedback = commands.add_parser("feedback")
    feedback.add_argument("message")
    commands.add_parser("feedback-list")
    respond = commands.add_parser("feedback-respond")
    respond.add_argument("feedback_id")
    respond.add_argument("--decision", required=True, choices=("continue", "ask", "pause"))
    respond.add_argument("--understanding", required=True)
    respond.add_argument("--reason", required=True)
    respond.add_argument("--impact", default="{}")
    respond.add_argument("--question")
    pause = commands.add_parser("pause")
    pause.add_argument("--reason", required=True)
    commands.add_parser("resume")
    revise = commands.add_parser("goal-revise")
    revise.add_argument("--reason", required=True)
    revise.add_argument("--requirement", required=True)
    route = commands.add_parser("route")
    route.add_argument("--target", required=True)
    route.add_argument("--reason", required=True)
    route.add_argument("--evidence", required=True)
    route.add_argument("--still-valid", nargs="*", default=[])
    route.add_argument("--invalidated", nargs="*", default=[])
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
        elif args.action == "next":
            result = app.next(project)
        elif args.action == "feedback":
            result = app.feedback(project, args.message)
        elif args.action == "feedback-list":
            result = app.feedback_list(project)
        elif args.action == "feedback-respond":
            try:
                impact = json.loads(args.impact)
                question = json.loads(args.question) if args.question else None
            except json.JSONDecodeError as exc:
                raise WorksError("E_FEEDBACK_RESPONSE_REQUIRED", str(exc)) from exc
            result = app.feedback_respond(
                project, args.feedback_id, args.decision, args.understanding,
                args.reason, impact, question,
            )
        elif args.action == "pause":
            result = app.pause(project, args.reason)
        elif args.action == "resume":
            result = app.resume(project)
        elif args.action == "goal-revise":
            requirement = Path(args.requirement)
            if not requirement.is_absolute():
                requirement = project / requirement
            result = app.goal_revise(project, args.reason, requirement)
        elif args.action == "route":
            result = app.route(
                project, args.target, args.reason, args.evidence,
                args.still_valid, args.invalidated,
            )
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
