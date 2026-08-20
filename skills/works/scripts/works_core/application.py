from __future__ import annotations

import json
import hashlib
from pathlib import Path
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
                "summaries": str(plan / "summaries"),
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
        if operation == "baseline-init" and (evidence / "baseline.json").exists():
            boundary = evidence / "service-boundary-baseline.json"
            if not boundary.exists():
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                               "--project-root", current["project_root"], "--state-dir", str(evidence)], operation)
            return {"ok": True, "operation": operation, "output": "baseline already initialized",
                    **store.refresh(plan, current)}
        if operation == "reopen":
            return self._reopen(plan, current, raw)
        command = self._command(plan, current, operation, raw)
        signature = self._signature(Path(current["project_root"]), command)
        attempt_key = f"{operation}:{current.get('current_req') or '-'}"
        previous = current.setdefault("attempts", {}).get(attempt_key)
        if previous and previous.get("signature") == signature and previous.get("result") == "failed":
            store.activity(plan, current, operation, "blocked", error="identical_failure_retry",
                           attempt=previous.get("count", 1))
            raise WorksError("E901_REPEAT_FAILURE", "identical failed action requires a workspace or strategy change",
                             previous)
        if operation == "test":
            try:
                self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "verify",
                               "--state-dir", str(evidence)], operation)
            except WorksError as exc:
                self._record_failure(plan, current, attempt_key, signature, operation, exc.code, exc.evidence)
                raise
        elif operation == "finalize":
            try:
                self._checked(
                    [sys.executable, str(self.scripts / "code_first.py"), "verify",
                     "--state-dir", str(evidence),
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
                self._record_failure(plan, current, attempt_key, signature, operation, exc.code, exc.evidence)
                raise
            return self._finalize(plan, current)
        proc = subprocess.run(command, cwd=Path(current["project_root"]), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode:
            code = self._classify(operation, proc.stdout)
            details = {"exit": proc.returncode, "output": proc.stdout[-4000:]}
            self._record_failure(plan, current, attempt_key, signature, operation, code, details)
            raise WorksError(code, f"{operation} failed", details)
        if operation == "baseline-init":
            self._checked([sys.executable, str(self.scripts / "service_boundary.py"), "init",
                           "--project-root", current["project_root"], "--state-dir", str(evidence)], operation)
        elif operation == "contract-check":
            contract = json.loads((plan / "requirement-contract.json").read_text())
            current["requirements"] = [row["id"] for row in contract["requirements"]]
            current["contract_valid"] = True
            current["contract_review_valid"] = False
            current["impact_valid"] = False
            (plan / "contract-review.json").unlink(missing_ok=True)
            current.setdefault("attempts", {}).pop("contract-review-check:-", None)
        elif operation == "contract-review-check":
            current["contract_review_valid"] = True
        elif operation == "impact-check":
            current["impact_valid"] = True
        elif operation == "implementation-review-check":
            current["implementation_review_valid"] = True
        elif operation in {"contract-review-init", "implementation-review-init"}:
            current.setdefault("attempts", {}).pop(f"{operation.removesuffix('-init')}-check:-", None)
        store.save(plan, current)
        current.setdefault("attempts", {}).pop(attempt_key, None)
        store.save(plan, current)
        store.activity(plan, current, operation, "passed", command=command)
        summary_name = (f"{operation}-{current.get('current_req')}"
                        if operation in {"implement", "test"} else operation)
        store.summarize(plan, current, summary_name, result="passed")
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
                    "--requirement", current["requirement"]]
        if operation in {"contract-review-init", "contract-review-check",
                         "implementation-review-init", "implementation-review-check"}:
            kind = "contract" if operation.startswith("contract-") else "implementation"
            action = "init" if operation.endswith("-init") else "validate"
            option = "--output" if action == "init" else "--file"
            return [sys.executable, str(self.scripts / "review_evidence.py"), action,
                    "--type", kind, option, str(plan / f"{kind}-review.json"),
                    "--contract", str(plan / "requirement-contract.json"),
                    "--project-root", current["project_root"]]
        if operation == "impact-init":
            return [sys.executable, str(self.scripts / "impact_map.py"), "init",
                    "--output", str(plan / "impact-map.json"),
                    *[item for req in current["requirements"] for item in ("--req", req)]]
        if operation == "impact-check":
            return [sys.executable, str(self.scripts / "impact_map.py"), "validate",
                    "--file", str(plan / "impact-map.json"), "--project-root", current["project_root"],
                    *[item for req in current["requirements"] for item in ("--req", req)]]
        if operation == "finalize":
            return []
        action = "init" if operation == "baseline-init" else operation
        runner = "code_first.py" if operation in {"implement", "test"} else "baseline.py"
        command = [sys.executable, str(self.scripts / runner), action]
        if operation == "baseline-init":
            command.extend(["--project-root", current["project_root"]])
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
            proc = subprocess.run(windows_command(row["command"]), cwd=Path(current["project_root"]), text=True,
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
            signature = self._signature(Path(current["project_root"]), [])
            self._record_failure(plan, current, "finalize:-", signature, "finalize",
                                 "E401_ACCEPTANCE_FAILED", results)
            raise WorksError("E401_ACCEPTANCE_FAILED", "one or more contract acceptance commands failed", results)
        current["implementation_review_valid"] = False
        (plan / "implementation-review.json").unlink(missing_ok=True)
        current.setdefault("attempts", {}).pop("implementation-review-check:-", None)
        store.save(plan, current)
        current.setdefault("attempts", {}).pop("finalize:-", None)
        store.save(plan, current)
        store.activity(plan, current, "finalize", "passed", acceptance=results)
        store.summarize(plan, current, "finalize", result="passed", acceptance=results)
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
        current["implementation_review_valid"] = False
        (plan / "implementation-review.json").unlink(missing_ok=True)
        current.setdefault("attempts", {}).pop("implementation-review-check:-", None)
        store.save(plan, current)
        store.activity(plan, current, "reopen", "passed", repair_req=repair_req, repair_of=req)
        store.summarize(plan, current, f"reopen-{repair_req}", result="passed", repair_of=req)
        return {"ok": True, "operation": "reopen", "repair_req": repair_req,
                "repair_of": req, **store.refresh(plan, current)}

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

    def _record_failure(self, plan: Path, current: dict, key: str, signature: str,
                        operation: str, error: str, evidence: object) -> None:
        previous = current.setdefault("attempts", {}).get(key, {})
        count = previous.get("count", 0) + 1
        current["attempts"][key] = {
            "count": count, "signature": signature, "result": "failed", "error": error,
            "required_strategy": "diagnose" if count == 1 else "alternative",
        }
        store.save(plan, current)
        store.activity(plan, current, operation, "failed", error=error, attempt=count, evidence=evidence)

    @staticmethod
    def _signature(project: Path, command: list[str]) -> str:
        status = subprocess.run(["git", "-C", str(project), "status", "--porcelain"], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        status = "\n".join(line for line in status.splitlines() if ".planning/" not in line)
        diff = subprocess.run(["git", "-C", str(project), "diff", "--binary", "HEAD", "--", ".",
                               ":(exclude).planning/**"], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        inputs = []
        for option in ("--file", "--contract"):
            if option in command and command.index(option) + 1 < len(command):
                path = Path(command[command.index(option) + 1])
                try:
                    inputs.append(path.read_text())
                except OSError:
                    inputs.append("<missing>")
        payload = json.dumps(command, ensure_ascii=False) + "\n" + status + "\n" + diff + "\n".join(inputs)
        return hashlib.sha256(payload.encode()).hexdigest()

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
                "contract-review-check": "E303_CONTRACT_REVIEW_FAILED",
                "implementation-review-check": "E402_IMPLEMENTATION_REVIEW_FAILED",
                "impact-check": "E301_INVALID_IMPACT_MAP"}.get(operation, "E900_COMMAND_FAILED")
