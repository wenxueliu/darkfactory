from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import discovery
from . import state as store
from .common import windows_command


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

    @staticmethod
    def _maven_project(current: dict) -> str:
        return current.get("discovery", {}).get("maven_project", current["project_root"])

    def status(self, project: Path) -> dict:
        plan, current = self.context(project)
        return {"ok": True, **store.refresh(plan, current, persist=False)}

    def recover(self, project: Path) -> dict:
        plan, current = self.context(project)
        current = store.refresh(plan, current, persist=False)
        activity_file = plan / "activity.jsonl"
        rows = []
        if activity_file.exists():
            for line in activity_file.read_text().splitlines():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        last_failure = next((row for row in reversed(rows) if row.get("result") in {"failed", "blocked"}), None)
        return {
            "ok": True, "recovered": True, **current,
            "last_activity": rows[-1] if rows else None,
            "last_failure": last_failure,
            "memory": {
                "activity": str(activity_file),
                "findings": str(plan / "findings.jsonl"),
                "decisions": str(plan / "decisions.jsonl"),
            },
        }

    def run(self, project: Path, operation: str, raw: list[str]) -> dict:
        plan, current = self.context(project)
        current = store.refresh(plan, current)
        evidence = Path(current["evidence_dir"])
        if operation == "note":
            return self._note(plan, current, raw)
        if operation not in current["allowed_actions"]:
            raise WorksError("E202_INVALID_STATE",
                             f"{operation} is not the next action; expected {current['next_action']['id']}")
        if operation == "preflight" and (evidence / "preflight.json").exists():
            boundary = evidence / "service-boundary-baseline.json"
            if not boundary.exists():
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                               "--project-root", self._maven_project(current),
                               "--state-dir", str(evidence)], operation)
            return {"ok": True, "operation": operation, "output": "preflight already completed",
                    **store.refresh(plan, current)}
        if operation == "reopen":
            return self._reopen(plan, current, raw)
        if operation == "rework":
            return self._rework(plan, current, raw)
        command = self._command(plan, current, operation, raw)
        attempt_key = f"{operation}:{current.get('current_req') or '-'}"
        if operation == "test":
            try:
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                               "--state-dir", str(evidence)], operation)
            except WorksError as exc:
                self._record_failure(plan, current, attempt_key, operation, exc.code, exc.evidence)
                raise
        elif operation == "finalize":
            try:
                self._checked(
                    [sys.executable, str(self.scripts / "code_first.py"), "verify",
                     "--state-dir", str(evidence), "--no-replay",
                     *[item for req in current["requirements"] for item in ("--req", req)]],
                    operation,
                )
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                               "--state-dir", str(evidence)], operation)
            except WorksError as exc:
                store.atomic_json(evidence / "final-verification.json", {
                    "passed": False, "phase": "code-first-or-boundary", "error": exc.code,
                    "evidence": exc.evidence, "recorded_at": time.time(),
                })
                self._record_failure(plan, current, attempt_key, operation, exc.code, exc.evidence)
                raise
            return self._finalize(plan, current)
        proc = subprocess.run(command, cwd=Path(current["project_root"]), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode:
            code = self._classify(operation, proc.stdout)
            details = {"exit": proc.returncode, "output": proc.stdout[-4000:]}
            self._record_failure(plan, current, attempt_key, operation, code, details)
            raise WorksError(code, f"{operation} failed", details)
        if operation == "preflight":
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                           "--project-root", self._maven_project(current),
                           "--state-dir", str(evidence)], operation)
        elif operation == "contract-check":
            contract = json.loads((plan / "requirement-contract.json").read_text())
            self._checked([sys.executable, str(self.scripts / "code_first.py"), "reuse-init",
                           "--state-dir", str(evidence)], operation)
            current["requirements"] = [row["id"] for row in contract["requirements"]]
            current["contract_valid"] = True
        store.save(plan, current)
        current.setdefault("attempts", {}).pop(attempt_key, None)
        store.save(plan, current)
        store.activity(plan, current, operation, "passed", command=command)
        return {"ok": True, "operation": operation, "output": proc.stdout, **store.refresh(plan, current)}

    def _command(self, plan: Path, current: dict, operation: str, raw: list[str]) -> list[str]:
        evidence = current["evidence_dir"]
        if operation in {"implement", "test"}:
            expected = "READY_FOR_IMPLEMENTATION" if operation == "implement" else "READY_FOR_TEST"
            if current["state"] != expected:
                raise WorksError("E202_INVALID_STATE", f"{operation} is forbidden in {current['state']}")
        if operation == "contract-init":
            return [sys.executable, str(self.scripts / "requirement_contract.py"), "init",
                    "--output", str(plan / "requirement-contract.json"),
                    "--requirement", current["requirement"]]
        if operation == "contract-check":
            return [sys.executable, str(self.scripts / "requirement_contract.py"), "validate",
                    "--file", str(plan / "requirement-contract.json"),
                    "--requirement", current["requirement"],
                    "--project-root", self._maven_project(current)]
        if operation == "finalize":
            return []
        action = operation
        runner = "code_first.py" if operation in {"implement", "test"} else "baseline.py"
        command = [sys.executable, str(self.scripts / runner), action]
        if operation == "preflight":
            command.extend(["--project-root", self._maven_project(current)])
        elif operation == "implement":
            current_req = current["current_req"]
            repair = next((row for row in current.get("repairs", []) if row.get("id") == current_req), None)
            contract_req = repair["of"] if repair else current_req
            command.extend(["--contract", str(plan / "requirement-contract.json"),
                            "--contract-req", contract_req])
        elif operation == "test":
            current_req = current["current_req"]
            repair = next((row for row in current.get("repairs", []) if row.get("id") == current_req), None)
            contract_req = repair["of"] if repair else current_req
            command.extend(["--contract", str(plan / "requirement-contract.json"),
                            "--contract-req", contract_req])
        command.extend(["--state-dir", evidence, *raw])
        return command

    def _finalize(self, plan: Path, current: dict) -> dict:
        evidence = Path(current["evidence_dir"])
        contract = json.loads((plan / "requirement-contract.json").read_text())
        results = []
        passed = True
        logs = plan / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        for row in contract["acceptance_commands"]:
            proc = subprocess.run(windows_command(row["command"]),
                                  cwd=Path(self._maven_project(current)), text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log = logs / f"acceptance-{row['id']}.log"
            log.write_text(proc.stdout)
            results.append({"id": row["id"], "covers": row["covers"], "command": row["command"],
                            "exit": proc.returncode, "log": str(log)})
            passed = passed and proc.returncode == 0
        store.atomic_json(evidence / "final-verification.json", {
            "passed": passed, "requirements": current["requirements"],
            "acceptance": results, "recorded_at": time.time(),
        })
        if not passed:
            self._record_failure(plan, current, "finalize:-", "finalize",
                                 "E401_ACCEPTANCE_FAILED", results)
            raise WorksError("E401_ACCEPTANCE_FAILED", "one or more contract acceptance commands failed", results)
        store.save(plan, current)
        current.setdefault("attempts", {}).pop("finalize:-", None)
        store.save(plan, current)
        store.activity(plan, current, "finalize", "passed", acceptance=results)
        return {"ok": True, "operation": "finalize", "acceptance": results,
                **store.refresh(plan, current)}

    def _reopen(self, plan: Path, current: dict, raw: list[str]) -> dict:
        if "--req" not in raw or raw.index("--req") + 1 >= len(raw):
            raise WorksError("E403_INVALID_REOPEN", "reopen requires --req REQ-ID")
        req = raw[raw.index("--req") + 1]
        if req not in current["requirements"]:
            raise WorksError("E403_INVALID_REOPEN", f"unknown requirement: {req}")
        evidence = Path(current["evidence_dir"])
        repairs = current.setdefault("repairs", [])
        suffix = f".repair-{1 + sum(row.get('of') == req for row in repairs)}"
        repair_req = f"{req[:64 - len(suffix)]}{suffix}"
        current["requirements"].append(repair_req)
        repairs.append({"id": repair_req, "of": req, "created_at": time.time()})
        for name in ("code-first-verify.json", "final-verification.json"):
            try:
                (evidence / name).unlink()
            except FileNotFoundError:
                pass
        store.save(plan, current)
        store.activity(plan, current, "reopen", "passed", repair_req=repair_req, repair_of=req)
        return {"ok": True, "operation": "reopen", "repair_req": repair_req,
                "repair_of": req, **store.refresh(plan, current)}

    def _rework(self, plan: Path, current: dict, raw: list[str]) -> dict:
        req = current.get("current_req")
        if "--req" not in raw or raw.index("--req") + 1 >= len(raw) or raw[raw.index("--req") + 1] != req:
            raise WorksError("E404_INVALID_REWORK", f"rework requires --req {req}")
        if "--reason" not in raw or raw.index("--reason") + 1 >= len(raw):
            raise WorksError("E404_INVALID_REWORK", "rework requires --reason production-fix")
        reason = raw[raw.index("--reason") + 1]
        if reason != "production-fix":
            raise WorksError("E404_INVALID_REWORK", "rework reason must be production-fix")
        attempt_key = f"test:{req}"
        if current.get("attempts", {}).get(attempt_key, {}).get("result") != "failed":
            raise WorksError("E404_INVALID_REWORK", "rework is allowed only after the current Req test failed")
        evidence = Path(current["evidence_dir"])
        slice_dir = evidence / "slices" / str(req)
        archive_root = evidence / "archive" / str(req)
        archive_root.mkdir(parents=True, exist_ok=True)
        sequence = 1 + len([path for path in archive_root.iterdir() if path.is_dir()])
        archive = archive_root / f"rework-{sequence}"
        archive.mkdir()
        for name in ("implementation.json", "test.log", "test-reports"):
            source = slice_dir / name
            if source.exists():
                shutil.move(str(source), str(archive / name))
        current.setdefault("reworks", []).append({
            "req": req, "reason": reason, "archive": str(archive), "created_at": time.time(),
        })
        current.setdefault("attempts", {}).pop(attempt_key, None)
        store.save(plan, current)
        store.activity(plan, current, "rework", "passed", req=req, reason=reason, archive=str(archive))
        return {"ok": True, "operation": "rework", "req": req, "archive": str(archive),
                **store.refresh(plan, current)}

    def _note(self, plan: Path, current: dict, raw: list[str]) -> dict:
        if ("--kind" not in raw or "--text" not in raw
                or raw.index("--kind") + 1 >= len(raw) or raw.index("--text") + 1 >= len(raw)):
            raise WorksError("E701_INVALID_NOTE", "note requires --kind finding|decision --text TEXT")
        kind = raw[raw.index("--kind") + 1]
        if kind not in {"finding", "decision"}:
            raise WorksError("E701_INVALID_NOTE", "note kind must be finding or decision")
        value = raw[raw.index("--text") + 1]
        req = raw[raw.index("--req") + 1] if "--req" in raw and raw.index("--req") + 1 < len(raw) else current.get("current_req")
        path = plan / ("findings.jsonl" if kind == "finding" else "decisions.jsonl")
        store.append_jsonl(path, {"time": time.time(), "req": req, "text": value})
        store.activity(plan, current, "note", "passed", kind=kind, req=req)
        return {"ok": True, "operation": "note", "kind": kind, "path": str(path)}

    def _record_failure(self, plan: Path, current: dict, key: str,
                        operation: str, error: str, evidence: object) -> None:
        previous = current.setdefault("attempts", {}).get(key, {})
        count = previous.get("count", 0) + 1
        current["attempts"][key] = {
            "count": count, "result": "failed", "error": error,
            "required_strategy": "diagnose" if count == 1 else "alternative",
        }
        store.save(plan, current)
        store.activity(plan, current, operation, "failed", error=error, attempt=count, evidence=evidence)

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
        if "production changed after implementation checkpoint" in lowered:
            return "E316_PRODUCTION_AFTER_IMPLEMENTATION"
        if "persistence dependency" in lowered:
            return "E510_BOUNDARY_VIOLATION"
        return {"implement": "E314_INVALID_IMPLEMENTATION", "test": "E315_INVALID_TEST",
                "contract-check": "E302_INVALID_REQUIREMENT_CONTRACT",
                }.get(operation, "E900_COMMAND_FAILED")
