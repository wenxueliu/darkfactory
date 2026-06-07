#!/usr/bin/env python3
"""user-prompt-clarifier — UserPromptSubmit hook for Harness multiagents.

Event: UserPromptSubmit
Purpose: Soft-detect implementation intent in user messages and surface a hint
         to invoke sw-requirements-clarifier before any code-writing begins.

This hook is INTENTIONALLY SOFT (additionalContext, not deny):
- False positives are expensive: blocking a "继续" follow-up because the user
  already clarified is bad UX
- The HARD gate is in ideation-gate.py (PreToolUse) which already denies
  Write/Edit to source code when ideation is not done
- This hook's job is to nudge, not enforce

Detection logic:
1. Match the user message against implementation verbs (zh + en)
2. If matched:
   a. Read _context/memory/sw-shared/requirements-tracker.yaml
   b. If tracker is missing OR has no in-progress requirements OR
      the message contains "新" / "new" / "创建" / "create" without any
      in-progress entry — emit a hint via additionalContext
3. Otherwise: exit 0 silently
"""

import json
import os
import re
import sys
from pathlib import Path

# Implementation verbs (Chinese + English) that suggest code-writing intent
IMPLEMENTATION_VERBS = re.compile(
    r"(?:实现|新增|创建|开发|做个?|写个?|加个?|改个?|修个?|添加|做个|添加个|做个新|写个新|"
    r"加个新|开发个|implement|add|create|build|develop|fix|new|make a|write a)",
    re.IGNORECASE,
)

# Tokens that signal "this is a follow-up on existing work, not a new ask"
FOLLOWUP_TOKENS = re.compile(
    r"(?:继续|接着|还有|然后|上次的|刚才的|上面那个|that one|continue|resume|next step|and then)",
    re.IGNORECASE,
)

# Tokens that signal "user knows they want clarifier" (skip nudge)
EXPLICIT_SKIP = re.compile(
    r"(?:直接做|跳过澄清|不用澄清|just do it|skip clarification|don't clarify)",
    re.IGNORECASE,
)


def detect_project_root(start_dir: str) -> str:
    """Walk up to find the project root."""
    markers = {".git", "_context", "pyproject.toml", "go.mod", "Cargo.toml", "package.json"}
    d = Path(start_dir).resolve()
    for _ in range(8):
        for marker in markers:
            if (d / marker).exists():
                return str(d)
        parent = d.parent
        if parent == d:
            break
        d = parent
    # No marker found — fall back to the input path (tests / fresh projects)
    return str(Path(start_dir).resolve())


def read_tracker_status(project_root: str) -> dict:
    """Read requirements-tracker.yaml. Return minimal status info.

    Returns:
        {
            'exists': bool,
            'has_in_progress': bool,
            'in_progress_ids': list[str],
            'parse_error': str | None,
        }
    """
    tracker_path = os.path.join(
        project_root, "_context", "memory", "sw-shared", "requirements-tracker.yaml"
    )
    if not os.path.isfile(tracker_path):
        return {
            "exists": False,
            "has_in_progress": False,
            "in_progress_ids": [],
            "parse_error": None,
        }

    try:
        import yaml
        with open(tracker_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except ImportError:
        return {
            "exists": True,
            "has_in_progress": False,
            "in_progress_ids": [],
            "parse_error": "PyYAML not installed; cannot parse tracker",
        }
    except Exception as e:
        return {
            "exists": True,
            "has_in_progress": False,
            "in_progress_ids": [],
            "parse_error": str(e),
        }

    # Find in_progress requirements. Schema may vary; support both
    # top-level list of dicts and dict with 'requirements' key.
    in_progress = []
    candidates = []
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        if "requirements" in data and isinstance(data["requirements"], list):
            candidates = data["requirements"]
        else:
            # Maybe flat dict: key is req ID
            for k, v in data.items():
                if isinstance(v, dict) and v.get("status") == "in_progress":
                    in_progress.append(k)

    for item in candidates:
        if isinstance(item, dict):
            if item.get("status") == "in_progress":
                rid = item.get("id") or item.get("requirement_id") or item.get("name") or "<unknown>"
                in_progress.append(str(rid))

    return {
        "exists": True,
        "has_in_progress": len(in_progress) > 0,
        "in_progress_ids": in_progress,
        "parse_error": None,
    }


def build_hint(status: dict, message: str) -> str:
    """Build the additionalContext hint text."""
    if not status["exists"]:
        return (
            "[Clarifier Hint — Harness] Detected implementation intent. "
            "No requirements-tracker.yaml found. "
            "Suggestion: Start a new requirement by calling sw-requirements-clarifier "
            "for 4-step progressive dialogue → spec document → gate check, "
            "BEFORE writing code. (This is a soft hint; ideation-gate.py will hard-block "
            "source writes if you skip this.)"
        )
    if status["parse_error"]:
        return (
            f"[Clarifier Hint — Harness] Detected implementation intent. "
            f"Tracker exists but could not be parsed: {status['parse_error']}. "
            f"Suggestion: Verify requirements-tracker.yaml is valid YAML and try again. "
            f"Or call sw-requirements-clarifier to start fresh."
        )
    if not status["has_in_progress"]:
        return (
            "[Clarifier Hint — Harness] Detected implementation intent. "
            "Tracker has no in-progress requirements. "
            "Suggestion: Start a new requirement via sw-requirements-clarifier. "
            "If this is a follow-up to a prior turn, mention the existing requirement ID."
        )
    # Tracker has in-progress; no nudge needed beyond a one-liner
    return (
        f"[Clarifier Hint — Harness] Detected implementation intent. "
        f"Active requirements: {', '.join(status['in_progress_ids'][:5])}. "
        f"If this task extends an existing requirement, proceed; "
        f"otherwise start a new one via sw-requirements-clarifier."
    )


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "") or input_data.get("user_prompt", "") or ""
    if not prompt:
        sys.exit(0)

    # Skip if user explicitly says "just do it"
    if EXPLICIT_SKIP.search(prompt):
        sys.exit(0)

    # Detect implementation intent
    if not IMPLEMENTATION_VERBS.search(prompt):
        sys.exit(0)

    cwd = input_data.get("cwd", "")
    project_root = detect_project_root(cwd)
    if not project_root:
        sys.exit(0)

    status = read_tracker_status(project_root)

    # Follow-up rule: if the prompt is a follow-up AND tracker already has in-progress
    # requirements, emit a minimal hint listing active IDs (so user knows what to extend).
    # Otherwise (no in-progress or fresh project) → silent.
    is_followup = FOLLOWUP_TOKENS.search(prompt) and not re.search(r"(?:新|new)\s", prompt, re.IGNORECASE)
    if is_followup:
        if not status.get("has_in_progress"):
            sys.exit(0)
        hint = (
            f"[Clarifier Hint — Harness] Active requirements: "
            f"{', '.join(status['in_progress_ids'][:5])}. "
            f"Continue with the existing one, or call sw-requirements-clarifier to start fresh."
        )
    else:
        hint = build_hint(status, prompt)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": hint,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
