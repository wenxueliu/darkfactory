from __future__ import annotations

import json
from pathlib import Path
import re
import time

from .common import append_jsonl, atomic_json


STATES = {
    "SETUP_REQUIRED", "CONTRACT_REQUIRED", "CONTRACT_REVIEW_REQUIRED", "IMPACT_REQUIRED",
    "MODULE_PLAN_REQUIRED", "WAVE_EXECUTION_REQUIRED", "READY_FOR_ACCEPTANCE",
    "IMPLEMENTATION_REVIEW_REQUIRED", "COMPLETE", "BLOCKED",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:40] or "change"


def create(project: Path, requirement: Path, discovery: dict) -> tuple[Path, dict]:
    planning = project / ".planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / f"works-{slug(requirement.stem)}"
    suffix = 2
    while plan.exists():
        plan = planning / f"works-{slug(requirement.stem)}-{suffix}"
        suffix += 1
    plan.mkdir()
    state = {
        "version": 2, "state": "SETUP_REQUIRED", "project_root": str(project),
        "requirement": str(requirement), "plan_dir": str(plan), "evidence_dir": str(plan / "evidence"),
        "requirements": [], "current_req": None, "contract_valid": False, "contract_review_valid": False,
        "impact_valid": False, "module_plan_valid": False, "current_wave": None,
        "implementation_review_valid": False,
        "discovery": discovery, "created_at": time.time(), "updated_at": time.time(),
    }
    save(plan, state)
    atomic_json(planning / ".active_works.json", {"plan_dir": str(plan)})
    return plan, state


def locate(project: Path) -> Path | None:
    marker = project / ".planning" / ".active_works.json"
    try:
        candidate = Path(json.loads(marker.read_text())["plan_dir"])
        if (candidate / "state.json").is_file():
            return candidate
    except (OSError, KeyError, json.JSONDecodeError):
        pass
    candidates = sorted((project / ".planning").glob("works-*/state.json"), key=lambda path: path.stat().st_mtime)
    return candidates[-1].parent if candidates else None


def load(plan: Path) -> dict:
    data = json.loads((plan / "state.json").read_text())
    if data.get("version") != 2:
        raise ValueError("unsupported works state version")
    return data


def save(plan: Path, state: dict) -> None:
    state["updated_at"] = time.time()
    atomic_json(plan / "state.json", state)


def activity(plan: Path, state: dict, action: str, result: str, **details: object) -> None:
    append_jsonl(plan / "activity.jsonl", {
        "time": time.time(), "state": state.get("state"), "req": state.get("current_req"),
        "action": action, "result": result, **details,
    })


def summarize(plan: Path, state: dict, action: str, **details: object) -> None:
    atomic_json(plan / "summaries" / f"{action}.json", {
        "time": time.time(), "action": action, "state": state.get("state"),
        "current_req": state.get("current_req"), "requirements": state.get("requirements", []),
        **details,
    })


def refresh(plan: Path, state: dict, persist: bool = True) -> dict:
    evidence = Path(state["evidence_dir"])
    baseline = evidence / "baseline.json"
    preflight = evidence / "preflight.json"
    if not baseline.exists() or not preflight.exists() or not json.loads(preflight.read_text()).get("passed"):
        stage = "SETUP_REQUIRED"
    elif not state.get("contract_valid") or not state["requirements"]:
        stage = "CONTRACT_REQUIRED"
    elif not state.get("contract_review_valid"):
        stage = "CONTRACT_REVIEW_REQUIRED"
    elif not state.get("impact_valid"):
        stage = "IMPACT_REQUIRED"
    elif not state.get("module_plan_valid"):
        stage = "MODULE_PLAN_REQUIRED"
    else:
        waves = state.get("waves", [])
        current_wave = next((index for index in range(1, len(waves) + 1)
                             if not (evidence / f"wave-{index}.json").exists()), None)
        state["current_wave"] = current_wave
        state["current_req"] = None
        if current_wave:
            stage = "WAVE_EXECUTION_REQUIRED"
        else:
            final = evidence / "final-verification.json"
            finalized = final.exists() and json.loads(final.read_text()).get("passed")
            if finalized:
                stage = "COMPLETE" if state.get("implementation_review_valid") else "IMPLEMENTATION_REVIEW_REQUIRED"
            else:
                stage = "READY_FOR_ACCEPTANCE"
    state["state"] = stage
    action_id = _next_action_id(stage, plan, evidence)
    state["allowed_actions"] = [NEXT_ACTION_OP[action_id]]
    state["forbidden_actions"] = [] if stage == "WAVE_EXECUTION_REQUIRED" else ["edit_production"]
    state["next_action_id"] = action_id
    state["next_action"] = next_action(action_id, state)
    if persist:
        save(plan, state)
    return state


def next_action(action_id: str, state: dict) -> dict:
    skills = {
        "run-fresh-contract-verifier-and-check": "impl-validator",
        "revise-contract-and-rerun-review": "impl-validator",
        "run-fresh-implementation-verifier-and-check": "impl-validator",
        "diagnose-review-and-reopen-requirement": "impl-validator",
    }
    references = {
        "complete-contract-and-check": "references/exploration.md",
        "complete-impact-map-and-check": "references/exploration.md",
        "complete-module-plan-and-check": "references/module-parallel.md",
        "dispatch-subagents-and-verify-wave": "references/module-parallel.md",
        "diagnose-and-reopen-failing-requirement": "references/diagnosis.md",
        "finalize": "references/verification.md",
    }
    evidence = {
        "complete-contract-and-check": "requirement-contract.json",
        "run-fresh-contract-verifier-and-check": "contract-review.json",
        "complete-impact-map-and-check": "impact-map.json",
        "complete-module-plan-and-check": "module-plan.json",
        "dispatch-subagents-and-verify-wave": f"evidence/wave-{state.get('current_wave')}.json",
        "finalize": "evidence/final-verification.json",
        "run-fresh-implementation-verifier-and-check": "implementation-review.json",
    }
    result = {
        "id": action_id, "state": state.get("state"), "req": state.get("current_req"),
        "skill": skills.get(action_id), "reference": references.get(action_id),
        "success_evidence": evidence.get(action_id),
    }
    if action_id == "dispatch-subagents-and-verify-wave":
        wave = state["current_wave"]
        task_ids = state["waves"][wave - 1]["tasks"]
        task_map = {task["id"]: task for task in state["module_tasks"]}
        result.update({"wave": wave, "parallel": True,
                       "tasks": [task_map[task_id] for task_id in task_ids]})
    return result


# logical next-action id -> the single CLI operation that completes it
NEXT_ACTION_OP = {
    "baseline-init": "baseline-init",
    "probe": "probe",
    "contract-init": "contract-init",
    "complete-contract-and-check": "contract-check",
    "contract-review-init": "contract-review-init",
    "run-fresh-contract-verifier-and-check": "contract-review-check",
    "revise-contract-and-rerun-review": "contract-check",
    "impact-init": "impact-init",
    "complete-impact-map-and-check": "impact-check",
    "module-plan-init": "module-plan-init",
    "complete-module-plan-and-check": "module-plan-check",
    "dispatch-subagents-and-verify-wave": "wave-check",
    "finalize": "finalize",
    "diagnose-and-reopen-failing-requirement": "reopen",
    "implementation-review-init": "implementation-review-init",
    "run-fresh-implementation-verifier-and-check": "implementation-review-check",
    "diagnose-review-and-reopen-requirement": "reopen",
    "report": "report",
    "inspect_evidence": "inspect_evidence",
}


def _next_action_id(stage: str, plan: Path, evidence: Path) -> str:
    if stage == "SETUP_REQUIRED":
        return "baseline-init" if not (evidence / "baseline.json").exists() else "probe"
    if stage == "CONTRACT_REQUIRED":
        return "contract-init" if not (plan / "requirement-contract.json").exists() else "complete-contract-and-check"
    if stage == "CONTRACT_REVIEW_REQUIRED":
        review = plan / "contract-review.json"
        result = review_result(review)
        if not review.exists():
            return "contract-review-init"
        if result and result != "PASS":
            return "revise-contract-and-rerun-review"
        return "run-fresh-contract-verifier-and-check"
    if stage == "IMPACT_REQUIRED":
        return "impact-init" if not (plan / "impact-map.json").exists() else "complete-impact-map-and-check"
    if stage == "MODULE_PLAN_REQUIRED":
        return "module-plan-init" if not (plan / "module-plan.json").exists() else "complete-module-plan-and-check"
    if stage == "WAVE_EXECUTION_REQUIRED":
        return "dispatch-subagents-and-verify-wave"
    if stage == "READY_FOR_ACCEPTANCE":
        final = evidence / "final-verification.json"
        failed = final.exists() and not json.loads(final.read_text()).get("passed")
        return "diagnose-and-reopen-failing-requirement" if failed else "finalize"
    if stage == "IMPLEMENTATION_REVIEW_REQUIRED":
        review = plan / "implementation-review.json"
        result = review_result(review)
        if not review.exists():
            return "implementation-review-init"
        if result and result != "PASS":
            return "diagnose-review-and-reopen-requirement"
        return "run-fresh-implementation-verifier-and-check"
    return "report" if stage == "COMPLETE" else "inspect_evidence"


def review_result(path: Path) -> str:
    try:
        data = json.loads(path.read_text())
        return str(data.get("result", "")) if isinstance(data, dict) else ""
    except (OSError, json.JSONDecodeError):
        return ""
