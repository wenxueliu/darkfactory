from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time


VERSION = 4
SKILL_ROOT = Path(__file__).resolve().parents[2]


def state_file(project: Path) -> Path:
    return project.resolve() / ".works" / "state.json"


def validate_workflow(workflow: dict) -> dict:
    if not isinstance(workflow, dict) or not isinstance(workflow.get("name"), str):
        raise ValueError("workflow.name must be a string")
    rows = workflow.get("steps")
    if not isinstance(rows, list) or not rows:
        raise ValueError("workflow.steps must be a non-empty list")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("every step requires a non-empty string id")
    if len(set(ids)) != len(ids):
        raise ValueError("step ids must be unique")
    known = set(ids)
    initial = workflow.get("initial_step", ids[0])
    if initial not in known:
        raise ValueError("initial_step must reference an existing step")
    for row in rows:
        if not isinstance(row.get("do"), str) or not row["do"].strip():
            raise ValueError(f"step {row['id']} requires a non-empty do prompt")
        if not isinstance(row.get("check"), str) or not row["check"].strip():
            raise ValueError(f"step {row['id']} requires a non-empty check prompt")
        validator = row.get("validator")
        if validator not in (None, "reuse_decisions", "implementation_reuse"):
            raise ValueError(f"step {row['id']} has an unknown validator")
        references = row.get("references", [])
        if (not isinstance(references, list)
                or any(not isinstance(value, str) or not value.strip()
                       for value in references)):
            raise ValueError(
                f"step {row['id']}.references must be a list of non-empty strings"
            )
        if len(set(references)) != len(references):
            raise ValueError(f"step {row['id']}.references must not contain duplicates")
        for value in references:
            reference = Path(value)
            if (reference.is_absolute() or "\\" in value
                    or reference.parts[:1] != ("references",)
                    or ".." in reference.parts):
                raise ValueError(
                    f"step {row['id']} reference must be a forward-slash path under references/"
                )
            if not (SKILL_ROOT / reference).is_file():
                raise ValueError(f"step {row['id']} reference does not exist: {value}")
        success = row.get("on_success")
        if success is not None and success not in known:
            raise ValueError(f"step {row['id']} has an unknown on_success target")
        failure = row.get("on_failure", {})
        if not isinstance(failure, dict):
            raise ValueError(f"step {row['id']}.on_failure must be an object")
        retries = failure.get("retries", 0)
        if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
            raise ValueError(f"step {row['id']} retries must be a non-negative integer")
        target = failure.get("goto", row["id"])
        if target not in known:
            raise ValueError(f"step {row['id']} has an unknown failure target")
    return {"version": 1, "name": workflow["name"], "initial_step": initial, "steps": rows}


def create(project: Path, workflow: dict) -> dict:
    path = state_file(project)
    if path.exists():
        return load(project)
    workflow = validate_workflow(workflow)
    state = {
        "version": VERSION,
        "project_root": str(project.resolve()),
        "workflow": workflow,
        "current_step": workflow["initial_step"],
        "completed": False,
        "failures": {},
        "last_check": None,
        "reuse_decisions": {},
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    save(project, state)
    return state


def load(project: Path) -> dict:
    path = state_file(project)
    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") in (2, 3):
        state = _migrate_v2(project, state)
    if state.get("version") != VERSION:
        raise ValueError("unsupported works state version")
    validate_workflow(state.get("workflow"))
    if state.get("current_step") not in step_map(state):
        raise ValueError("current_step does not exist in workflow")
    return state


def _migrate_v2(project: Path, state: dict) -> dict:
    previous_version = state.get("version")
    state["version"] = VERSION
    if "reuse_decisions" not in state:
        state["reuse_decisions"] = {}
    workflow = state.get("workflow", {})
    if (workflow.get("name") == "java-brownfield-development"
            and not state.get("completed")):
        current_workflow = json.loads(
            (SKILL_ROOT / "assets" / "workflows" / "development.json").read_text(encoding="utf-8")
        )
        state["workflow"] = validate_workflow(current_workflow)
        if previous_version == 2 and state.get("current_step") not in {
                "requirements", "exploration", "reuse_analysis"}:
            state["current_step"] = "reuse_analysis"
        elif state.get("current_step") == "unit_test":
            state["current_step"] = "test_case_design"
        elif state.get("current_step") not in {
                "requirements", "exploration", "reuse_analysis", "test_case_design",
                "implementation", "compile", "regression_test", "build_test_fix"}:
            state["current_step"] = "reuse_analysis"
    save(project, state)
    return state


def save(project: Path, state: dict) -> None:
    path = state_file(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.time()
    fd, temporary = tempfile.mkstemp(prefix="state-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def step_map(state: dict) -> dict[str, dict]:
    return {row["id"]: row for row in state["workflow"]["steps"]}


def response(state: dict) -> dict:
    current = None if state["completed"] else step_map(state)[state["current_step"]]
    return {
        "ok": True,
        "state_file": str(state_file(Path(state["project_root"]))),
        "next_action": None if current is None else {
            "step": current["id"],
            "do": current["do"],
            "check": current["check"],
            "references_to_read": current.get("references", []),
            "command": "check",
        },
        **state,
    }
