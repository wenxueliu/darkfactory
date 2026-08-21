from __future__ import annotations

from pathlib import Path
import subprocess
import time

from . import state as store


class WorksError(RuntimeError):
    def __init__(self, code: str, message: str, details: object = None):
        super().__init__(message)
        self.code = code
        self.details = details


class Application:
    def init(self, project: Path, workflow: dict) -> dict:
        project = project.resolve()
        if not project.is_dir():
            raise WorksError("E101_PROJECT_NOT_FOUND", f"project does not exist: {project}")
        try:
            return store.response(store.create(project, workflow))
        except ValueError as exc:
            raise WorksError("E102_INVALID_WORKFLOW", str(exc)) from exc

    def status(self, project: Path) -> dict:
        return store.response(self._load(project))

    def check(self, project: Path, passed: bool, evidence: str,
              command: list[str] | None = None) -> dict:
        state = self._load(project)
        if state["completed"]:
            raise WorksError("E204_ALREADY_COMPLETE", "works is already complete")
        step = store.step_map(state)[state["current_step"]]
        state["last_check"] = {
            "step": step["id"], "passed": passed, "evidence": evidence,
            "command": command, "checked_at": time.time(),
        }
        if passed:
            state["failures"][step["id"]] = 0
            target = step.get("on_success")
            if target is None:
                state["completed"] = True
            else:
                state["current_step"] = target
        else:
            count = state["failures"].get(step["id"], 0) + 1
            state["failures"][step["id"]] = count
            policy = step.get("on_failure", {})
            if count > policy.get("retries", 0):
                state["current_step"] = policy.get("goto", step["id"])
                state["failures"][step["id"]] = 0
        store.save(project, state)
        result = store.response(state)
        result["check_passed"] = passed
        return result

    def check_command(self, project: Path, command: list[str]) -> dict:
        if not command:
            raise WorksError("E203_CHECK_REQUIRED", "check requires a command after --")
        state = self._load(project)
        process = subprocess.run(
            command, cwd=Path(state["project_root"]), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        evidence = f"exit={process.returncode}\n{process.stdout[-4000:]}"
        return self.check(project, process.returncode == 0, evidence, command)

    @staticmethod
    def _load(project: Path) -> dict:
        try:
            return store.load(project.resolve())
        except FileNotFoundError as exc:
            raise WorksError("E201_NO_STATE", "run init first", str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise WorksError("E202_INVALID_STATE", str(exc)) from exc
