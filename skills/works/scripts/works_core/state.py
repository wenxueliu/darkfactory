from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time


VERSION = 6
SKILL_ROOT = Path(__file__).resolve().parents[2]


def state_file(project: Path) -> Path:
    return project.resolve() / ".works" / "state.json"


def works_dir(project: Path) -> Path:
    return project.resolve() / ".works"


def goal_file(project: Path) -> Path:
    return works_dir(project) / "goal.json"


def decisions_file(project: Path) -> Path:
    return works_dir(project) / "decisions.json"


def events_file(project: Path) -> Path:
    return works_dir(project) / "events.jsonl"


def inbox_dir(project: Path) -> Path:
    return works_dir(project) / "inbox"


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
        if validator not in (
                None, "reuse_decisions", "test_case_design_artifact",
                "implementation_reuse", "test_generation_mapping"):
            raise ValueError(f"step {row['id']} has an unknown validator")
        subagent = row.get("subagent")
        if subagent is not None and (
                not isinstance(subagent, dict)
                or set(subagent) != {"role", "fresh_context"}
                or not isinstance(subagent.get("role"), str)
                or not subagent["role"].strip()
                or not isinstance(subagent.get("fresh_context"), bool)):
            raise ValueError(
                f"step {row['id']}.subagent requires role and fresh_context"
            )
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
        purpose = row.get("purpose")
        route_when = row.get("route_when")
        if purpose is not None and (not isinstance(purpose, str) or not purpose.strip()):
            raise ValueError(f"step {row['id']}.purpose must be a non-empty string")
        if route_when is not None and (not isinstance(route_when, str) or not route_when.strip()):
            raise ValueError(f"step {row['id']}.route_when must be a non-empty string")
        next_steps = row.get("next")
        if next_steps is not None:
            if (not isinstance(next_steps, list)
                    or any(not isinstance(value, str) or value not in known
                           for value in next_steps)
                    or len(set(next_steps)) != len(next_steps)):
                raise ValueError(f"step {row['id']}.next must contain unique defined steps")
            policy = row.get("forward_policy", "next_only")
            if policy not in ("next_only", "declared", "any_defined"):
                raise ValueError(f"step {row['id']} has an unknown forward_policy")
            forward = row.get("forward_targets", [])
            if (not isinstance(forward, list)
                    or any(not isinstance(value, str) or value not in known for value in forward)
                    or len(set(forward)) != len(forward)):
                raise ValueError(
                    f"step {row['id']}.forward_targets must contain unique defined steps"
                )
            if policy != "declared" and forward:
                raise ValueError(f"step {row['id']}.forward_targets requires declared policy")
            if not isinstance(row.get("complete", False), bool):
                raise ValueError(f"step {row['id']}.complete must be boolean")
        success = row.get("on_success")
        if next_steps is None and success is not None and success not in known:
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
    initial = workflow["initial_step"]
    state = {
        "version": VERSION,
        "project_root": str(project.resolve()),
        "workflow": workflow,
        "execution_state": "running",
        "current_step": initial,
        "completed": False,
        "visited_steps": [initial],
        "goal_revision": 1,
        "pending_feedback": [],
        "active_question": None,
        "route_history": [],
        "step_results": {initial: {"status": "active"}},
        "awaiting_route": False,
        "failures": {},
        "last_check": None,
        "reuse_decisions": {},
        "test_case_design_artifact": None,
        "test_generation_mapping": {},
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    directory = works_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    inbox_dir(project).mkdir(parents=True, exist_ok=True)
    requirement = project.resolve() / "requirement.md"
    objective = requirement.read_text(encoding="utf-8").strip() if requirement.is_file() else ""
    write_json(goal_file(project), {
        "revision": 1,
        "objective": objective,
        "acceptance_criteria": [],
        "constraints": [],
        "open_questions": [],
        "requirement": requirement_metadata(project, requirement) if requirement.is_file() else None,
    })
    write_json(decisions_file(project), {
        "current": [], "superseded": [], "open_questions": [],
    })
    append_event(project, "initialized", {"workflow": workflow["name"]})
    save(project, state)
    return state


def load(project: Path) -> dict:
    path = state_file(project)
    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") in (2, 3, 4, 5):
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
    initial = state.get("current_step")
    state.setdefault("execution_state", "completed" if state.get("completed") else "running")
    state.setdefault("visited_steps", [initial] if initial else [])
    state.setdefault("goal_revision", 1)
    state.setdefault("pending_feedback", [])
    state.setdefault("active_question", None)
    state.setdefault("route_history", [])
    state.setdefault("step_results", {initial: {"status": "active"}} if initial else {})
    state.setdefault("awaiting_route", False)
    if "reuse_decisions" not in state:
        state["reuse_decisions"] = {}
    if "test_case_design_artifact" not in state:
        state["test_case_design_artifact"] = None
    if "test_generation_mapping" not in state:
        state["test_generation_mapping"] = {}
    workflow = state.get("workflow", {})
    if (workflow.get("name") == "java-brownfield-development"
            and not state.get("completed")):
        current_workflow = json.loads(
            (SKILL_ROOT / "assets" / "workflows" / "development.json").read_text(encoding="utf-8")
        )
        state["workflow"] = validate_workflow(current_workflow)
        if previous_version == 4 and state.get("current_step") in {
                "implementation", "compile", "regression_test", "build_test_fix"}:
            state["current_step"] = "test_case_design"
        elif previous_version == 2 and state.get("current_step") not in {
                "requirements", "exploration", "reuse_analysis"}:
            state["current_step"] = "reuse_analysis"
        elif state.get("current_step") == "unit_test":
            state["current_step"] = "test_case_design"
        elif state.get("current_step") not in {
                "requirements", "exploration", "reuse_analysis", "test_case_design",
                "implementation", "compile", "test_generation", "regression_test",
                "build_test_fix"}:
            state["current_step"] = "reuse_analysis"
    directory = works_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    inbox_dir(project).mkdir(parents=True, exist_ok=True)
    if not goal_file(project).exists():
        write_json(goal_file(project), {
            "revision": 1, "objective": "", "acceptance_criteria": [],
            "constraints": [], "open_questions": [], "requirement": None,
        })
    if not decisions_file(project).exists():
        write_json(decisions_file(project), {
            "current": [], "superseded": [], "open_questions": [],
        })
    save(project, state)
    return state


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f"{path.stem}-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_event(project: Path, event_type: str, payload: dict) -> None:
    event = {"type": event_type, "created_at": time.time(), **payload}
    path = events_file(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def requirement_metadata(project: Path, requirement: Path) -> dict:
    import hashlib

    resolved = requirement.resolve()
    resolved.relative_to(project.resolve())
    raw = resolved.read_bytes()
    return {
        "path": resolved.relative_to(project.resolve()).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def load_goal(project: Path) -> dict:
    return json.loads(goal_file(project).read_text(encoding="utf-8"))


def load_feedback(project: Path) -> list[dict]:
    result = []
    for path in sorted(inbox_dir(project).glob("HF-*.json")):
        result.append(json.loads(path.read_text(encoding="utf-8")))
    return result


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
    project = Path(state["project_root"])
    return {
        "ok": True,
        "state_file": str(state_file(Path(state["project_root"]))),
        "goal": load_goal(project),
        "current_step_contract": None if current is None else step_card(current),
        "allowed_targets": [] if current is None else allowed_targets(state),
        "recent_decisions": state.get("route_history", [])[-5:],
        "next_action": None if current is None else {
            "type": "execute_step",
            "step": current["id"],
            "do": current["do"],
            "check": current["check"],
            "references_to_read": current.get("references", []),
            "subagent": current.get("subagent"),
            "command": "check",
        },
        **state,
    }


def step_card(step: dict) -> dict:
    return {
        key: step[key] for key in ("id", "purpose", "route_when", "do", "check")
        if key in step
    }


def allowed_targets(state: dict) -> list[str]:
    current = step_map(state)[state["current_step"]]
    ordered_ids = [row["id"] for row in state["workflow"]["steps"]]
    allowed = set(state.get("visited_steps", []))
    allowed.add(current["id"])
    allowed.update(current.get("next", []))
    policy = current.get("forward_policy", "next_only")
    if policy == "declared":
        allowed.update(current.get("forward_targets", []))
    elif policy == "any_defined":
        index = ordered_ids.index(current["id"])
        allowed.update(ordered_ids[index + 1:])
    result = [step_id for step_id in ordered_ids if step_id in allowed]
    if current.get("complete", False):
        result.append("__complete__")
    return result
