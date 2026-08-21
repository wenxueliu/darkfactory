from __future__ import annotations

import json
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
    REUSE_TIERS = ("current_class", "same_layer", "cross_layer")
    REUSE_GATES = (
        "semantic_match",
        "callable",
        "no_recursion",
        "dependency_direction",
        "proxy_safe",
        "transaction_compatible",
        "contract_compatible",
    )

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
        if passed and step.get("validator") == "reuse_decisions":
            decisions = self._validate_reuse_decisions(evidence)
            state["reuse_decisions"] = decisions
        if passed and step.get("validator") == "implementation_reuse":
            self._validate_implementation_evidence(
                evidence,
                state.get("reuse_decisions", {}),
                Path(state["project_root"]),
            )
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

    @classmethod
    def _validate_reuse_decisions(cls, evidence: str) -> dict[str, dict]:
        try:
            payload = json.loads(evidence)
        except json.JSONDecodeError as exc:
            raise WorksError(
                "E205_REUSE_DECISION_REQUIRED",
                "reuse_analysis evidence must be valid JSON",
            ) from exc
        rows = payload.get("reuse_decisions") if isinstance(payload, dict) else None
        if (not isinstance(payload, dict) or set(payload) != {"reuse_decisions"}
                or not isinstance(rows, list) or not rows):
            raise WorksError(
                "E205_REUSE_DECISION_REQUIRED",
                "reuse_decisions must be a non-empty list",
            )

        validated: dict[str, dict] = {}
        tier_rank = {tier: rank for rank, tier in enumerate(cls.REUSE_TIERS)}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "feature", "selected", "candidates", "search_evidence"
            }:
                raise WorksError("E205_REUSE_DECISION_REQUIRED", "each decision must be an object")
            feature = row.get("feature")
            candidates = row.get("candidates")
            searched = row.get("search_evidence")
            selected = row.get("selected")
            if not isinstance(feature, str) or not feature.strip() or feature in validated:
                raise WorksError(
                    "E205_REUSE_DECISION_REQUIRED",
                    "each decision requires a unique non-empty feature",
                )
            if not isinstance(candidates, list):
                raise WorksError("E205_REUSE_DECISION_REQUIRED", f"{feature}: candidates must be a list")
            if not isinstance(searched, dict):
                raise WorksError(
                    "E205_REUSE_DECISION_REQUIRED",
                    f"{feature}: search_evidence must be an object",
                )

            by_symbol: dict[str, dict] = {}
            for candidate in candidates:
                if not isinstance(candidate, dict) or set(candidate) != {
                    "symbol", "tier", "feasible", "gates", "evidence", "reject_reasons"
                }:
                    raise WorksError("E205_REUSE_DECISION_REQUIRED", f"{feature}: invalid candidate")
                symbol = candidate.get("symbol")
                tier = candidate.get("tier")
                feasible = candidate.get("feasible")
                candidate_evidence = candidate.get("evidence")
                reasons = candidate.get("reject_reasons", [])
                gates = candidate.get("gates")
                if (not isinstance(symbol, str) or not symbol.strip() or symbol in by_symbol
                        or tier not in tier_rank or not isinstance(feasible, bool)
                        or not isinstance(candidate_evidence, str) or not candidate_evidence.strip()
                        or not isinstance(reasons, list)
                        or any(not isinstance(reason, str) or not reason.strip() for reason in reasons)
                        or not isinstance(gates, dict) or set(gates) != set(cls.REUSE_GATES)
                        or any(not isinstance(gates[name], bool) for name in cls.REUSE_GATES)):
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED", f"{feature}: malformed candidate"
                    )
                if feasible != all(gates.values()):
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: feasible must equal the result of all hard gates",
                    )
                if not feasible and not reasons:
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: rejected candidate {symbol} requires reject_reasons",
                    )
                if feasible and reasons:
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: feasible candidate {symbol} must not have reject_reasons",
                    )
                by_symbol[symbol] = candidate

            if selected is None:
                if any(candidate["feasible"] for candidate in candidates):
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: fallback is forbidden while a feasible candidate exists",
                    )
                required_search_tiers = cls.REUSE_TIERS
            else:
                if not isinstance(selected, str) or selected not in by_symbol:
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: selected must name a listed candidate",
                    )
                chosen = by_symbol[selected]
                if not chosen["feasible"]:
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED", f"{feature}: selected candidate is infeasible"
                    )
                chosen_rank = tier_rank[chosen["tier"]]
                if any(candidate["feasible"] and tier_rank[candidate["tier"]] < chosen_rank
                       for candidate in candidates):
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: a higher-priority feasible candidate must be selected",
                    )
                required_search_tiers = cls.REUSE_TIERS[:chosen_rank + 1]
                if any(tier_rank[candidate["tier"]] > chosen_rank for candidate in candidates):
                    raise WorksError(
                        "E205_REUSE_DECISION_REQUIRED",
                        f"{feature}: lower-priority candidates are forbidden after selection",
                    )
            if set(searched) != set(required_search_tiers):
                raise WorksError(
                    "E205_REUSE_DECISION_REQUIRED",
                    f"{feature}: search_evidence must contain exactly the tiers reached",
                )
            if any(
                not isinstance(searched.get(tier), str) or not searched[tier].strip()
                for tier in required_search_tiers
            ):
                raise WorksError(
                    "E205_REUSE_DECISION_REQUIRED",
                    f"{feature}: search_evidence must cover every tier through the selection",
                )
            validated[feature] = row
        return validated

    @staticmethod
    def _validate_implementation_evidence(
        evidence: str, decisions: dict[str, dict], project_root: Path
    ) -> None:
        if not decisions:
            raise WorksError(
                "E205_REUSE_DECISION_REQUIRED",
                "implementation requires persisted reuse decisions",
            )
        try:
            payload = json.loads(evidence)
        except json.JSONDecodeError as exc:
            raise WorksError(
                "E206_IMPLEMENTATION_REUSE_MISMATCH",
                "implementation evidence must be valid JSON",
            ) from exc
        rows = payload.get("implementation_reuse") if isinstance(payload, dict) else None
        if (not isinstance(payload, dict) or set(payload) != {"implementation_reuse"}
                or not isinstance(rows, list) or len(rows) != len(decisions)):
            raise WorksError(
                "E206_IMPLEMENTATION_REUSE_MISMATCH",
                "implementation_reuse must contain exactly one row per feature",
            )
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "feature", "action", "symbol", "call_site"
            }:
                raise WorksError("E206_IMPLEMENTATION_REUSE_MISMATCH", "invalid implementation row")
            feature = row.get("feature")
            action = row.get("action")
            symbol = row.get("symbol")
            call_site = row.get("call_site")
            if (feature not in decisions or feature in seen
                    or not isinstance(call_site, str) or not call_site.strip()):
                raise WorksError(
                    "E206_IMPLEMENTATION_REUSE_MISMATCH",
                    "implementation row must identify one persisted feature and a call site",
                )
            selected = decisions[feature]["selected"]
            expected_action = "invoke" if selected is not None else "fallback"
            if action != expected_action or symbol != selected:
                raise WorksError(
                    "E206_IMPLEMENTATION_REUSE_MISMATCH",
                    f"{feature}: implementation must match the persisted reuse decision",
                )
            source_file, separator, line_text = call_site.rpartition(":")
            try:
                line_number = int(line_text) if separator else 0
            except ValueError:
                line_number = 0
            path = (project_root / source_file).resolve()
            try:
                path.relative_to(project_root.resolve())
                source_lines = path.read_text(encoding="utf-8").splitlines()
            except (ValueError, OSError):
                source_lines = []
            if line_number < 1 or line_number > len(source_lines):
                raise WorksError(
                    "E206_IMPLEMENTATION_REUSE_MISMATCH",
                    f"{feature}: call_site must resolve to an existing source line",
                )
            if selected is not None:
                method = selected.split("#", 1)[-1].split("(", 1)[0]
                if method == selected:
                    method = selected.rsplit(".", 1)[-1]
                if f"{method}(" not in source_lines[line_number - 1].replace(" ", ""):
                    raise WorksError(
                        "E206_IMPLEMENTATION_REUSE_MISMATCH",
                        f"{feature}: selected invocation was not found at call_site",
                    )
            seen.add(feature)

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
