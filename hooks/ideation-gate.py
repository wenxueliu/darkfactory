#!/usr/bin/env python3
"""ideation-gate — PreToolUse hook for Harness multiagents.

Event: PreToolUse (Agent)
Purpose: Blocks delegation to implementation agents before requirement
         clarification (ideation phase) has been started.
         "Explicit surface clarity does NOT equal clarified requirements."

Check logic:
  1. No requirements-tracker.yaml AND no requirements/*.md → BLOCK (not started)
  2. Requirements exist but ideation status != done → WARN but allow
  3. Requirements exist and ideation done → ALLOW
"""

import json
import os
import re
import sys
from pathlib import Path

# Implementation agents that require completed ideation first
IMPLEMENTATION_PATTERN = re.compile(
    r"sw-tdd-agent|sw-plan-executor|sw-worktree-controller",
    re.IGNORECASE,
)


def detect_project_root(start_dir: str) -> str:
    """Walk up from start_dir to find the project root."""
    markers = {".git", "pyproject.toml", "go.mod", "Cargo.toml", "package.json"}
    d = Path(start_dir).resolve()
    while True:
        for marker in markers:
            if (d / marker).exists():
                return str(d)
        parent = d.parent
        if parent == d:
            break
        d = parent
    return ""


def parse_yaml_ideation_status(tracker_path: str) -> bool:
    """Return True if ideation phase status is 'done' in the tracker YAML."""
    try:
        with open(tracker_path) as f:
            content = f.read()
    except OSError:
        return False

    in_ideation = False
    for line in content.split("\n"):
        stripped = line.rstrip()
        if stripped in ("  ideation:",) or stripped.startswith("  ideation "):
            in_ideation = True
            continue
        # Exit ideation section: non-empty, not 4-space indented, not a comment
        if (
            in_ideation
            and stripped
            and not stripped.startswith("    ")
            and not stripped.startswith("  #")
        ):
            if not stripped.startswith("  ") or (
                len(stripped) >= 2
                and stripped[:2] == "  "
                and len(stripped) > 2
                and stripped[2] != " "
            ):
                in_ideation = False
                continue
        if in_ideation and "status:" in stripped and "done" in stripped:
            return True
    return False


def has_requirements_artifacts(project_root: str) -> bool:
    """Check if any requirements artifacts exist in the project."""
    root = Path(project_root)

    # Check 1: requirements-tracker.yaml
    tracker = root / "_context" / "memory" / "sw-shared" / "requirements-tracker.yaml"
    if tracker.exists():
        return True

    # Check 2: requirements/ directory with .md files
    req_dir = root / "requirements"
    if req_dir.is_dir():
        if any(req_dir.glob("*.md")):
            return True

    # Check 3: _context/memory/sw-shared/ requirement/clarification files
    mem_dir = root / "_context" / "memory" / "sw-shared"
    if mem_dir.is_dir():
        for pattern in ["*requirement*", "*clarif*"]:
            if any(mem_dir.glob(pattern)):
                return True

    return False


def is_implementation_agent(tool_input: dict) -> bool:
    """Check if the Agent tool call targets an implementation agent."""
    subagent_type = tool_input.get("subagent_type") or tool_input.get("subagentType") or ""
    description = tool_input.get("description", "")
    for field in (subagent_type, description):
        if IMPLEMENTATION_PATTERN.search(field):
            return True
    return False


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    session_id = input_data.get("session_id", "")

    if not session_id or tool_name != "Agent":
        sys.exit(0)

    cwd = input_data.get("cwd", "")
    project_root = detect_project_root(cwd)
    if not project_root:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})

    if not is_implementation_agent(tool_input):
        sys.exit(0)

    # Check ideation status
    tracker_file = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )

    if os.path.isfile(tracker_file):
        if parse_yaml_ideation_status(tracker_file):
            sys.exit(0)  # ideation done → allow

        # Ideation started but not done → warn but allow
        reason = (
            "Ideation Gate WARNING: requirements-tracker.yaml exists but ideation phase "
            "is not marked 'done'. You are delegating to an implementation agent before "
            "completing requirement clarification. Consider delegating to "
            "sw-requirements-clarifier first if requirements are not yet fully clarified."
        )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            }
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

    if has_requirements_artifacts(project_root):
        sys.exit(0)  # artifacts exist → ideation in progress, allow

    # No requirements work found → BLOCK
    subagent_type = tool_input.get("subagent_type") or tool_input.get("subagentType") or "unknown"
    reason = (
        f"Ideation Gate BLOCKED: No requirements documents found. You are trying to "
        f"delegate to an implementation agent ({subagent_type}) but requirement "
        f"clarification has not been started. Required flow: "
        f"1) Delegate to sw-requirements-clarifier for 4-step progressive clarification, "
        f"2) Value assessment via sw-value-judgment, "
        f"3) Requirements gate PASS. "
        f"Only then may you delegate to implementation agents. "
        f"Explicit surface clarity does NOT equal clarified requirements — "
        f"clarification IS the check."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(2)


if __name__ == "__main__":
    main()
