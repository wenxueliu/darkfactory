#!/usr/bin/env python3
"""Inject the using-harness bootstrap skill when a session starts."""

from hook_common import PLUGIN_ROOT, emit_context


def main() -> int:
    skill_path = PLUGIN_ROOT / "skills" / "using-harness" / "SKILL.md"
    try:
        skill = skill_path.read_text(encoding="utf-8")
    except OSError:
        skill = "Error reading using-harness skill"
    context = (
        "<EXTREMELY_IMPORTANT>\n"
        "You are running the Harness multi-agent system.\n\n"
        "**Below is the full content of your 'using-harness' skill — your "
        "introduction to the Harness multi-agent skill system. For all other "
        "skills, use the 'Skill' tool:**\n\n"
        f"{skill}\n</EXTREMELY_IMPORTANT>"
    )
    emit_context("SessionStart", context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
