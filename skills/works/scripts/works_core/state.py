from __future__ import annotations

import json
from pathlib import Path
import re
import time

from .common import append_jsonl, atomic_json


STATES = {
    "SETUP_REQUIRED", "CONTRACT_REQUIRED",
    "READY_FOR_IMPLEMENTATION", "READY_FOR_TEST", "READY_FOR_ACCEPTANCE",
    "COMPLETE", "BLOCKED",
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
        "requirements": [], "current_req": None, "contract_valid": False,
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


def refresh(plan: Path, state: dict, persist: bool = True) -> dict:
    evidence = Path(state["evidence_dir"])
    baseline = evidence / "baseline.json"
    preflight = evidence / "preflight.json"
    if not baseline.exists() or not preflight.exists() or not json.loads(preflight.read_text()).get("passed"):
        stage = "SETUP_REQUIRED"
    elif not state.get("contract_valid") or not state["requirements"]:
        stage = "CONTRACT_REQUIRED"
    else:
        current = None
        implementation_checkpointed = False
        for req in state["requirements"]:
            slice_dir = evidence / "slices" / req
            if not (slice_dir / "test.json").exists():
                current = req
                implementation_checkpointed = (slice_dir / "implementation.json").exists()
                break
        state["current_req"] = current
        if current:
            stage = "READY_FOR_TEST" if implementation_checkpointed else "READY_FOR_IMPLEMENTATION"
        else:
            verification = evidence / "code-first-verify.json"
            verified = verification.exists() and json.loads(verification.read_text()).get("passed")
            final = evidence / "final-verification.json"
            finalized = final.exists() and json.loads(final.read_text()).get("passed")
            if verified and finalized:
                stage = "COMPLETE"
            else:
                stage = "READY_FOR_ACCEPTANCE"
    state["state"] = stage
    action_id = _next_action_id(stage, plan, evidence, state)
    state["allowed_actions"] = [NEXT_ACTION_OP[action_id]]
    state["forbidden_actions"] = [] if stage == "READY_FOR_IMPLEMENTATION" else ["edit_production"]
    state["next_action_id"] = action_id
    state["next_action"] = next_action(action_id, state, plan)
    if persist:
        save(plan, state)
    return state


def next_action(action_id: str, state: dict, plan: Path | None = None) -> dict:
    subagents = {}
    skills = {}
    references = {
        "complete-contract-and-check": "references/requirement-contract.md",
        "checkpoint-current-implementation": "references/code-first.md",
        "test-current-implementation": "references/code-first.md",
        "rework-current-implementation": "references/code-first.md",
        "diagnose-and-reopen-failing-requirement": "references/diagnosis.md",
        "finalize": "references/verification.md",
    }
    evidence = {
        "complete-contract-and-check": "requirement-contract.json",
        "checkpoint-current-implementation": f"evidence/slices/{state.get('current_req')}/implementation.json",
        "test-current-implementation": f"evidence/slices/{state.get('current_req')}/test.json",
        "finalize": "evidence/final-verification.json",
    }
    result = {
        "id": action_id, "state": state.get("state"), "req": state.get("current_req"),
        "skill": skills.get(action_id), "subagent": subagents.get(action_id),
        "reference": references.get(action_id),
        "success_evidence": evidence.get(action_id),
    }
    if action_id == "checkpoint-current-implementation" and plan is not None:
        contract_req = state.get("current_req")
        repair = next((row for row in state.get("repairs", []) if row.get("id") == contract_req), None)
        if repair:
            contract_req = repair.get("of")
        try:
            contract = json.loads((plan / "requirement-contract.json").read_text())
            row = next(item for item in contract["requirements"] if item["id"] == contract_req)
            result["reuse_decision"] = row["implementation"]["reuse"]
        except (OSError, json.JSONDecodeError, KeyError, StopIteration, TypeError):
            result["reuse_decision"] = None
    return result


# logical next-action id -> the single CLI operation that completes it
NEXT_ACTION_OP = {
    "preflight": "preflight",
    "contract-init": "contract-init",
    "complete-contract-and-check": "contract-check",
    "checkpoint-current-implementation": "implement",
    "test-current-implementation": "test",
    "rework-current-implementation": "rework",
    "finalize": "finalize",
    "diagnose-and-reopen-failing-requirement": "reopen",
    "report": "report",
    "inspect_evidence": "inspect_evidence",
}


def _next_action_id(stage: str, plan: Path, evidence: Path, state: dict) -> str:
    if stage == "SETUP_REQUIRED":
        return "preflight"
    if stage == "CONTRACT_REQUIRED":
        return "contract-init" if not (plan / "requirement-contract.json").exists() else "complete-contract-and-check"
    if stage == "READY_FOR_IMPLEMENTATION":
        return "checkpoint-current-implementation"
    if stage == "READY_FOR_TEST":
        req = _current_req_from_evidence(evidence)
        attempt = state.get("attempts", {}).get(f"test:{req}", {})
        if attempt.get("result") == "failed":
            return "rework-current-implementation"
        return "test-current-implementation"
    if stage == "READY_FOR_ACCEPTANCE":
        final = evidence / "final-verification.json"
        failed = final.exists() and not json.loads(final.read_text()).get("passed")
        return "diagnose-and-reopen-failing-requirement" if failed else "finalize"
    return "report" if stage == "COMPLETE" else "inspect_evidence"


def _current_req_from_evidence(evidence: Path) -> str | None:
    """Return the first implementation slice that does not yet have passing test evidence."""
    slices = evidence / "slices"
    if not slices.is_dir():
        return None
    for path in slices.iterdir():
        if path.is_dir() and (path / "implementation.json").exists() and not (path / "test.json").exists():
            return path.name
    return None
