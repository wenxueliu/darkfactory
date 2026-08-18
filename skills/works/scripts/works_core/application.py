from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import time

from . import discovery
from . import state as store


class WorksError(RuntimeError):
    def __init__(self, code: str, message: str, evidence: object = None):
        super().__init__(message)
        self.code, self.evidence = code, evidence


class Application:
    def __init__(self, scripts: Path):
        self.scripts = scripts

    def doctor(self, start: Path) -> dict:
        found = discovery.discover(start)
        if "error" in found:
            raise WorksError(found["error"], "project discovery failed", found)
        project = Path(found["project"])
        return {"ok": True, "checks": {
            "python_3_10_plus": sys.version_info >= (3, 10),
            "git_worktree": discovery.git_root(project) is not None,
            "maven_project": Path(found["pom"]).is_file(),
            "project_writable": project.exists() and project.is_dir(),
        }, "discovery": found}

    def init(self, start: Path) -> dict:
        found = discovery.discover(start)
        if "error" in found:
            raise WorksError(found["error"], "project discovery failed", found)
        plan, current = store.create(Path(found["project"]), Path(found["requirement"]), found)
        return {"ok": True, "plan": str(plan), **store.refresh(plan, current)}

    def context(self, project: Path) -> tuple[Path, dict]:
        plan = store.locate(project.resolve())
        if not plan:
            raise WorksError("E201_NO_PLAN", "no active works state", {"project": str(project)})
        return plan, store.load(plan)

    def status(self, project: Path) -> dict:
        plan, current = self.context(project)
        return {"ok": True, **store.refresh(plan, current)}

    def set_requirements(self, project: Path, reqs: list[str]) -> dict:
        if (not reqs or len(reqs) != len(set(reqs))
                or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", req) for req in reqs)):
            raise WorksError("E302_INVALID_REQUIREMENTS", "Req IDs must be non-empty, ordered and unique")
        plan, current = self.context(project)
        current = store.refresh(plan, current)
        if current["state"] != "IMPACT_REQUIRED":
            raise WorksError("E202_INVALID_STATE", f"set-reqs is forbidden in {current['state']}")
        current["requirements"] = reqs
        current["impact_valid"] = False
        store.save(plan, current)
        return store.refresh(plan, current)

    def run(self, project: Path, operation: str, raw: list[str]) -> dict:
        plan, current = self.context(project)
        current = store.refresh(plan, current)
        evidence = Path(current["evidence_dir"])
        allowed_states = {
            "tdd-init": {"SETUP_REQUIRED"}, "probe": {"SETUP_REQUIRED"},
            "impact-init": {"IMPACT_REQUIRED"}, "impact-check": {"IMPACT_REQUIRED"},
            "red": {"READY_FOR_RED"}, "green": {"READY_FOR_IMPLEMENTATION"},
            "verify": {"READY_FOR_ACCEPTANCE"}, "accept": {"READY_FOR_ACCEPTANCE"},
        }
        if current["state"] not in allowed_states[operation]:
            raise WorksError("E202_INVALID_STATE", f"{operation} is forbidden in {current['state']}")
        if operation not in current["allowed_actions"]:
            raise WorksError("E202_INVALID_STATE",
                             f"{operation} is not the next action; expected {current['allowed_actions'][0]}")
        if operation == "tdd-init" and (evidence / "baseline.json").exists():
            boundary = evidence / "service-boundary-baseline.json"
            if not boundary.exists():
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                               "--project-root", current["project_root"], "--state-dir", str(evidence)], operation)
            return {"ok": True, "operation": operation, "output": "baseline already initialized",
                    **store.refresh(plan, current)}
        command = self._command(plan, current, operation, raw)
        if operation == "green":
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                           "--state-dir", str(evidence)], operation)
        elif operation == "accept":
            self._checked(
                [sys.executable, str(self.scripts / "tdd_slice.py"), "verify",
                 "--state-dir", str(evidence),
                 *[item for req in current["requirements"] for item in ("--req", req)]],
                operation,
            )
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                           "--state-dir", str(evidence)], operation)
        proc = subprocess.run(command, cwd=Path(current["project_root"]), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if operation == "accept":
            name = raw[raw.index("--name") + 1]
            log = plan / "logs" / f"acceptance-{name}.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(proc.stdout)
            current.setdefault("acceptance", {})[name] = {
                "exit": proc.returncode, "command": raw[raw.index("--") + 1:],
                "recorded_at": time.time(), "log": str(log),
            }
            store.save(plan, current)
        if proc.returncode:
            raise WorksError(self._classify(operation, proc.stdout), f"{operation} failed",
                             {"exit": proc.returncode, "output": proc.stdout[-4000:]})
        if operation == "tdd-init":
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                           "--project-root", current["project_root"], "--state-dir", str(evidence)], operation)
        elif operation == "impact-check":
            current["impact_valid"] = True
        elif operation == "verify":
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                           "--state-dir", str(evidence)], operation)
        store.save(plan, current)
        return {"ok": True, "operation": operation, "output": proc.stdout, **store.refresh(plan, current)}

    def _command(self, plan: Path, current: dict, operation: str, raw: list[str]) -> list[str]:
        evidence = current["evidence_dir"]
        if operation in {"red", "green"}:
            expected = "READY_FOR_RED" if operation == "red" else "READY_FOR_IMPLEMENTATION"
            if current["state"] != expected:
                raise WorksError("E202_INVALID_STATE", f"{operation} is forbidden in {current['state']}")
        if operation == "impact-init":
            return [sys.executable, str(self.scripts / "impact_map.py"), "init",
                    "--output", str(plan / "impact-map.json"),
                    *[item for req in current["requirements"] for item in ("--req", req)]]
        if operation == "impact-check":
            return [sys.executable, str(self.scripts / "impact_map.py"), "validate",
                    "--file", str(plan / "impact-map.json"), "--project-root", current["project_root"],
                    *[item for req in current["requirements"] for item in ("--req", req)]]
        if operation == "accept":
            if "--name" not in raw or "--" not in raw:
                raise WorksError("E402_INVALID_ACCEPTANCE", "accept requires --name NAME -- COMMAND")
            command = raw[raw.index("--") + 1:]
            if not command:
                raise WorksError("E402_INVALID_ACCEPTANCE", "accept command cannot be empty")
            return command
        action = "init" if operation == "tdd-init" else operation
        command = [sys.executable, str(self.scripts / "tdd_slice.py"), action]
        if operation == "tdd-init":
            command.extend(["--project-root", current["project_root"]])
        command.extend(["--state-dir", evidence, *raw])
        return command

    def _checked(self, command: list[str], operation: str) -> None:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode:
            raise WorksError(self._classify(operation, proc.stdout), f"{operation} postcondition failed",
                             {"exit": proc.returncode, "output": proc.stdout[-4000:]})

    @staticmethod
    def _classify(operation: str, output: str) -> str:
        lowered = output.lower()
        if "skip configuration" in lowered:
            return "E203_TESTS_SKIPPED"
        if "production differs" in lowered:
            return "E312_PRODUCTION_BEFORE_RED"
        if "persistence dependency" in lowered:
            return "E510_BOUNDARY_VIOLATION"
        return {"red": "E311_INVALID_RED", "green": "E313_INVALID_GREEN",
                "impact-check": "E301_INVALID_IMPACT_MAP"}.get(operation, "E900_COMMAND_FAILED")
