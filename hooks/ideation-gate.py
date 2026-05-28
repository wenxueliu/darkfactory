#!/usr/bin/env python3
"""ideation-gate — PreToolUse hook for Harness multiagents.

Event: PreToolUse (Agent, Write, Edit)
Purpose: Blocks ANY code-writing action before requirement clarification
         (ideation phase) has completed.
         "Explicit surface clarity does NOT equal clarified requirements."

Check logic (strict):
  1. Read requirements-tracker.yaml → check ideation.status == done
  2. If tracker absent OR ideation not done → BLOCK (deny)
  3. If ideation done → ALLOW

This hook monitors TWO paths:
  - Agent tool targeting implementation agents (sw-tdd-agent, etc.)
  - Write/Edit tool targeting source code files (not test/config/doc)
"""

import json
import os
import re
import sys
from pathlib import Path

# Implementation agents that require completed ideation first
IMPLEMENTATION_PATTERN = re.compile(
    r"sw-tdd-agent|sw-plan-executor|sw-worktree-controller|sw-controller",
    re.IGNORECASE,
)

# Source code file patterns (write-protected before ideation done)
# Test files, config files, and docs are exempt (TDD writes tests first)
SOURCE_CODE_PATTERNS = [
    re.compile(r"\.(py|js|ts|tsx|jsx|java|go|rs|c|cpp|h|hpp|cs|rb|php|swift|kt)$"),
]

# Tools monitored for source code writes
MONITORED_TOOLS = {"Agent", "Write", "Edit"}


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
        # Exit ideation section
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


def is_source_code_file(file_path: str) -> bool:
    """Check if the file path looks like a source code file (not test/config/doc)."""
    path = Path(file_path)
    # Test files are exempt (TDD principle: write test first, then implement)
    if "test" in path.name.lower() or path.name.startswith("test_"):
        return False
    # Config/doc files are exempt
    exempt_patterns = [
        ".md", ".rst", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".json", ".txt", ".csv",
    ]
    for pat in exempt_patterns:
        if path.name.endswith(pat):
            return False
    # Check source code extension
    for pat in SOURCE_CODE_PATTERNS:
        if pat.search(file_path):
            return True
    return False


def is_write_to_source_code(tool_name: str, tool_input: dict) -> bool:
    """Check if the tool call would write/edit a source code file."""
    if tool_name not in ("Write", "Edit"):
        return False
    file_path = tool_input.get("file_path", "")
    return bool(file_path and is_source_code_file(file_path))


def is_implementation_agent(tool_input: dict) -> bool:
    """Check if the Agent tool call targets an implementation agent."""
    subagent_type = tool_input.get("subagent_type") or tool_input.get("subagentType") or ""
    description = tool_input.get("description", "") or ""
    skill = tool_input.get("skill") or ""
    for field in (subagent_type, description, skill):
        if IMPLEMENTATION_PATTERN.search(field):
            return True
    return False


def check_ideation_completed(project_root: str) -> bool:
    """Check if ideation phase is marked 'done' in the requirements tracker."""
    tracker_file = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )
    if not os.path.isfile(tracker_file):
        return False
    return parse_yaml_ideation_status(tracker_file)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    session_id = input_data.get("session_id", "")

    if not session_id or tool_name not in MONITORED_TOOLS:
        sys.exit(0)

    cwd = input_data.get("cwd", "")
    project_root = detect_project_root(cwd)
    if not project_root:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})

    # Determine if this action needs ideation protection
    needs_ideation = False
    target_desc = "unknown"

    if tool_name == "Agent":
        if is_implementation_agent(tool_input):
            needs_ideation = True
            target_desc = (
                tool_input.get("subagent_type")
                or tool_input.get("subagentType")
                or tool_input.get("skill")
                or "implementation-agent"
            )
    elif tool_name in ("Write", "Edit"):
        if is_write_to_source_code(tool_name, tool_input):
            needs_ideation = True
            target_desc = tool_input.get("file_path", "source-file")

    if not needs_ideation:
        sys.exit(0)

    # --- Ideation check: HARD gate ---
    is_done = check_ideation_completed(project_root)

    if is_done:
        sys.exit(0)  # ideation done → allow

    # Ideation NOT done → DENY (with different messages for "not started" vs "in progress")
    tracker_path = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )
    if os.path.isfile(tracker_path):
        # Ideation started but not done → DENY (was "warn but allow", upgraded to hard gate)
        reason = (
            f"Ideation Gate DENIED: requirements-tracker.yaml exists but ideation phase "
            f"is NOT marked 'done'. You are trying to write code via ({target_desc}) "
            f"before completing requirement clarification. "
            f"Complete the ideation phase first: delegate to sw-requirements-clarifier, "
            f"pass the requirements gate, and mark ideation.status = done in the tracker. "
            f"Explicit surface clarity does NOT equal clarified requirements."
        )
    else:
        # No requirements work found → DENY
        reason = (
            f"Ideation Gate DENIED: No requirements documents found. You are trying to "
            f"write code via ({target_desc}) but requirement clarification has not been "
            f"started. Required flow: "
            f"1) Delegate to sw-requirements-clarifier for 4-step progressive clarification, "
            f"2) Value assessment via sw-value-judgment, "
            f"3) Requirements gate PASS. "
            f"Only then may you write implementation code. "
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
