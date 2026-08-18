from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import time


STATES = {
    "SETUP_REQUIRED", "CONTRACT_REQUIRED", "IMPACT_REQUIRED", "READY_FOR_RED", "READY_FOR_IMPLEMENTATION",
    "READY_FOR_ACCEPTANCE", "COMPLETE", "BLOCKED",
}


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


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
        "requirements": [], "current_req": None, "contract_valid": False, "impact_valid": False,
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


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


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


def refresh(plan: Path, state: dict) -> dict:
    evidence = Path(state["evidence_dir"])
    baseline = evidence / "baseline.json"
    preflight = evidence / "preflight.json"
    if not baseline.exists() or not preflight.exists() or not json.loads(preflight.read_text()).get("passed"):
        stage = "SETUP_REQUIRED"
    elif not state.get("contract_valid") or not state["requirements"]:
        stage = "CONTRACT_REQUIRED"
    elif not state.get("impact_valid"):
        stage = "IMPACT_REQUIRED"
    else:
        current = None
        open_red = False
        for req in state["requirements"]:
            slice_dir = evidence / "slices" / req
            if not (slice_dir / "green.json").exists():
                current = req
                open_red = (slice_dir / "red.json").exists()
                break
        state["current_req"] = current
        if current:
            stage = "READY_FOR_IMPLEMENTATION" if open_red else "READY_FOR_RED"
        else:
            verification = evidence / "tdd-verify.json"
            verified = verification.exists() and json.loads(verification.read_text()).get("passed")
            final = evidence / "final-verification.json"
            finalized = final.exists() and json.loads(final.read_text()).get("passed")
            if verified and finalized:
                stage = "COMPLETE"
            else:
                stage = "READY_FOR_ACCEPTANCE"
    state["state"] = stage
    state["allowed_actions"], state["forbidden_actions"] = actions(stage)
    if stage == "SETUP_REQUIRED":
        state["allowed_actions"] = ["tdd-init"] if not baseline.exists() else ["probe"]
    elif stage == "CONTRACT_REQUIRED":
        contract = plan / "requirement-contract.json"
        state["allowed_actions"] = ["contract-init"] if not contract.exists() else ["complete-contract-and-check"]
    elif stage == "IMPACT_REQUIRED":
        impact = plan / "impact-map.json"
        if not impact.exists():
            state["allowed_actions"] = ["impact-init"]
        else:
            state["allowed_actions"] = ["complete-impact-map-and-check"]
    elif stage == "READY_FOR_ACCEPTANCE":
        final = evidence / "final-verification.json"
        failed = final.exists() and not json.loads(final.read_text()).get("passed")
        state["allowed_actions"] = ["diagnose-and-reopen-failing-requirement"] if failed else ["finalize"]
    action_id = state["allowed_actions"][0]
    state["next_action_id"] = action_id
    state["next_action"] = next_action(action_id, state)
    save(plan, state)
    return state


def next_action(action_id: str, state: dict) -> dict:
    skills = {
        "complete-contract-and-check": "sw-codebase-explorer",
        "complete-impact-map-and-check": "sw-codebase-explorer",
        "establish-red-for-current-requirement": "tdd",
        "implement-current-requirement-and-run-green": "tdd",
        "diagnose-and-reopen-failing-requirement": "sw-systematic-debugging",
        "finalize": "sw-verification-before-completion",
    }
    evidence = {
        "complete-contract-and-check": "requirement-contract.json",
        "complete-impact-map-and-check": "impact-map.json",
        "establish-red-for-current-requirement": f"evidence/slices/{state.get('current_req')}/red.json",
        "implement-current-requirement-and-run-green": f"evidence/slices/{state.get('current_req')}/green.json",
        "finalize": "evidence/final-verification.json",
    }
    return {
        "id": action_id, "state": state.get("state"), "req": state.get("current_req"),
        "skill": skills.get(action_id), "success_evidence": evidence.get(action_id),
    }


def actions(stage: str) -> tuple[list[str], list[str]]:
    mapping = {
        "SETUP_REQUIRED": ["tdd-init", "probe"],
        "CONTRACT_REQUIRED": ["contract-init", "contract-check"],
        "IMPACT_REQUIRED": ["impact-init", "impact-check"],
        "READY_FOR_RED": ["establish-red-for-current-requirement"],
        "READY_FOR_IMPLEMENTATION": ["implement-current-requirement-and-run-green"],
        "READY_FOR_ACCEPTANCE": ["finalize", "reopen"],
        "COMPLETE": ["report"],
        "BLOCKED": ["inspect_evidence"],
    }
    forbidden = [] if stage == "READY_FOR_IMPLEMENTATION" else ["edit_production"]
    return mapping[stage], forbidden
