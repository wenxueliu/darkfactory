#!/usr/bin/env python3
"""ideation-gate — PreToolUse hook for Harness multiagents.

Event: PreToolUse (Agent, Write, Edit)
Purpose: Blocks ANY code-writing action before requirement clarification
         (ideation phase) has completed.
         "Explicit surface clarity does NOT equal clarified requirements."

Check logic (strict):
  1. Read requirements-tracker.yaml via PyYAML → check ideation.status == done
  2. Validate spec content: requirements/{id}.md exists with all mandatory
     sections and each section is at least 50 characters
  3. If tracker absent OR ideation not done OR spec validation fails → BLOCK
  4. If ideation done AND spec valid → ALLOW

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


def parse_yaml_ideation_status(tracker_path: str) -> tuple[bool, str | None, list[str]]:
    """Read tracker via PyYAML; return (ideation_done, active_req_id, validation_errors).

    Returns (False, None, [...errors]) if file is missing, malformed, or unclear.
    Returns (True, req_id, [...errors]) if ideation.status is 'done' for some req.
    Returns (False, req_id, [...errors]) if ideation.status is not 'done'.
    """
    if not os.path.isfile(tracker_path):
        return False, None, [f"requirements-tracker.yaml not found at {tracker_path}"]

    try:
        import yaml
    except ImportError:
        return False, None, [
            "PyYAML is not installed; cannot parse requirements-tracker.yaml. "
            "Install with: pip install pyyaml"
        ]

    try:
        with open(tracker_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, None, [f"requirements-tracker.yaml is not valid YAML: {e}"]
    except OSError as e:
        return False, None, [f"Cannot read requirements-tracker.yaml: {e}"]

    if not isinstance(data, dict):
        return False, None, [
            f"requirements-tracker.yaml root must be a mapping, got {type(data).__name__}"
        ]

    # Find any requirement with ideation.status == 'done'
    # Schema: { requirements: [ { id: ..., phases: { ideation: { status: 'done' } } } ] }
    # OR:    { REQ-XXX: { phases: { ideation: { status: 'done' } } } }
    # OR:    { phases: { ideation: { status: 'done' } } }  (singleton, single active req)
    candidates: list[tuple[str | None, dict]] = []
    if "requirements" in data and isinstance(data["requirements"], list):
        for item in data["requirements"]:
            if isinstance(item, dict):
                rid = item.get("id") or item.get("requirement_id")
                candidates.append((rid, item))
    elif "phases" in data and isinstance(data["phases"], dict):
        candidates.append((data.get("id") or data.get("requirement_id"), data))
    else:
        # Flat dict: top-level keys might be req IDs
        for k, v in data.items():
            if isinstance(v, dict) and "phases" in v:
                candidates.append((k, v))

    for rid, item in candidates:
        phases = item.get("phases", {}) if isinstance(item, dict) else {}
        ideation = phases.get("ideation", {}) if isinstance(phases, dict) else {}
        status = ideation.get("status") if isinstance(ideation, dict) else None
        if status == "done":
            return True, rid, []

    # No 'done' status found. Return the first candidate's ID for context.
    first_id = candidates[0][0] if candidates else None
    return False, first_id, []


# Mandatory sections in requirements/{id}.md spec
MANDATORY_SPEC_SECTIONS = [
    "问题陈述",        # Problem statement
    "用户故事",        # User stories
    "验收标准",        # Acceptance criteria
    "非功能需求",      # Non-functional requirements
    "约束",            # Constraints
    "风险",            # Risks (or 风险与假设 / 风险与决策)
]
MIN_SECTION_LENGTH = 50  # chars; below this, section is considered empty


def validate_spec_content(project_root: str, req_id: str | None) -> list[str]:
    """Verify that requirements/{id}.md exists and has all mandatory sections.

    Returns list of error messages (empty list = valid).
    """
    errors: list[str] = []
    if not req_id:
        return errors  # No req_id to validate against; tracker-level check handles this

    # Try common spec filenames
    candidates = [
        os.path.join(project_root, "_context", "memory", "sw-shared", "requirements", f"{req_id}.md"),
        os.path.join(project_root, "_context", "memory", "sw-shared", "requirements", f"REQ-{req_id}.md"),
        os.path.join(project_root, "requirements", f"{req_id}.md"),
    ]
    spec_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not spec_path:
        return [
            f"Spec file not found. Expected one of: {', '.join(candidates)}. "
            f"sw-requirements-clarifier must write requirements/{{id}}.md before marking ideation done."
        ]

    try:
        content = Path(spec_path).read_text(encoding="utf-8")
    except OSError as e:
        return [f"Cannot read spec file {spec_path}: {e}"]

    # Find which mandatory sections are present and validate length
    missing: list[str] = []
    too_short: list[str] = []
    for section in MANDATORY_SPEC_SECTIONS:
        # Match `## {section}` or `## {section} xxx` (allow sub-headings)
        pattern = re.compile(rf"^##\s+{re.escape(section)}(?:\s|$)", re.MULTILINE)
        m = pattern.search(content)
        if not m:
            # Try softer match (some sections have prefixes like 风险与假设)
            if not re.search(rf"^##.*{re.escape(section[:2])}", content, re.MULTILINE):
                missing.append(section)
            continue
        # Find end of section (next ## heading or EOF)
        start = m.end()
        next_heading = re.search(r"^##\s+", content[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(content)
        section_text = content[start:end].strip()
        if len(section_text) < MIN_SECTION_LENGTH:
            too_short.append(f"{section} ({len(section_text)} chars)")

    if missing:
        errors.append(f"Spec {spec_path} is missing mandatory sections: {', '.join(missing)}")
    if too_short:
        errors.append(
            f"Spec {spec_path} has too-short sections (< {MIN_SECTION_LENGTH} chars): "
            f"{', '.join(too_short)}"
        )
    return errors


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


def check_ideation_completed(project_root: str) -> tuple[bool, list[str], str | None]:
    """Check if ideation phase is marked 'done' in the requirements tracker.

    Returns (is_done, errors, req_id). When is_done is True, errors should
    be empty. When is_done is False, errors explain why.
    """
    tracker_file = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )
    is_done, req_id, parse_errors = parse_yaml_ideation_status(tracker_file)
    if not is_done:
        return False, parse_errors or ["ideation phase is not marked 'done' in tracker"], req_id

    # Tracker says done; verify spec content as a second-line check
    spec_errors = validate_spec_content(project_root, req_id)
    if spec_errors:
        return False, spec_errors, req_id

    return True, [], req_id


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
    is_done, gate_errors, req_id = check_ideation_completed(project_root)

    if is_done:
        sys.exit(0)  # ideation done AND spec valid → allow

    # Ideation NOT done → DENY (with different messages for "not started" vs "in progress" vs "spec invalid")
    tracker_path = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )
    error_details = "; ".join(gate_errors) if gate_errors else "ideation not done"

    if not os.path.isfile(tracker_path):
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
    elif req_id and gate_errors and "Spec file not found" in error_details:
        # Tracker says done but spec doesn't exist
        reason = (
            f"Ideation Gate DENIED: Tracker marks {req_id}.ideation as 'done' but "
            f"requirements/{req_id}.md is missing. Either: "
            f"(a) Restore the spec file from version control, or "
            f"(b) Reset ideation.status to in_progress and re-run sw-requirements-clarifier. "
            f"Details: {error_details}"
        )
    elif req_id and gate_errors:
        # Tracker says done but spec content is incomplete
        reason = (
            f"Ideation Gate DENIED: Tracker marks {req_id}.ideation as 'done' but "
            f"spec validation failed. {error_details} "
            f"Fix the spec or reset ideation.status to in_progress."
        )
    else:
        # Ideation started but not done → DENY
        reason = (
            f"Ideation Gate DENIED: requirements-tracker.yaml exists but ideation phase "
            f"is NOT marked 'done'. You are trying to write code via ({target_desc}) "
            f"before completing requirement clarification. "
            f"Complete the ideation phase first: delegate to sw-requirements-clarifier, "
            f"pass the requirements gate, and mark ideation.status = done in the tracker. "
            f"Explicit surface clarity does NOT equal clarified requirements."
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
