#!/usr/bin/env python3
"""Harness Multiagents — One-Click Install Script.

Copies Agent skill files from the multiagents source tree to Claude Code, Codex,
or both.

Installation targets:
  --claude           .claude/skills/  .claude/agents/   (project)
                     ~/.claude/skills/  ~/.claude/agents/   (user)
  --codex            .agents/skills/  (project)  or  ~/.agents/skills/  (user)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# ---- constants ----------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_SKILLS = SCRIPT_DIR / "skills"
SOURCE_AGENTS = SCRIPT_DIR / "agents"

MINIMAL_SKILLS = {
    "sw-controller",
    "sw-tdd-agent",
    "sw-reviewer-logic",
    "sw-worktree-controller",
}

PLATFORM_CLAUDE = "claude"
PLATFORM_CODEX = "codex"

COPY_INDENT = "  "

# ---- platform target definitions ----------------------------------------
# Each platform has its own sub-path under a user/home or project root.

PLATFORM_CONFIG = {
    PLATFORM_CLAUDE: {
        "label": "Claude Code",
        "project_skills": ".claude/skills",
        "user_skills": Path.home() / ".claude" / "skills",
        "project_agents": ".claude/agents",
        "user_agents": Path.home() / ".claude" / "agents",
        "invoke_hint": "/sw-controller",
    },
    PLATFORM_CODEX: {
        "label": "Codex",
        "project_skills": ".agents/skills",
        "user_skills": Path.home() / ".agents" / "skills",
        "project_agents": ".agents/skills",
        "user_agents": Path.home() / ".agents" / "skills",
        "invoke_hint": "sw-controller (after restart)",
    },
}


# ---- helpers ------------------------------------------------------------

def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"{COPY_INDENT}{msg}")


def success(msg: str) -> None:
    print(f"SUCCESS: {msg}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="One-click Harness multi-agent skill installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "EXAMPLES:\n"
            "  python install.py                                    # current dir, Claude\n"
            "  python install.py --codex                            # current dir, Codex\n"
            "  python install.py --claude --codex                   # current dir, both\n"
            "  python install.py --target /path/to/project          # specific project\n"
            "  python install.py --user                             # user-wide, Claude\n"
            "  python install.py --user --claude --codex --minimal  # user-wide, both\n"
            "  python install.py --target /tmp/test --dry-run       # preview\n"
            "\n"
            "MINIMAL SKILLS (4):\n"
            "  sw-controller          Top-level orchestrator\n"
            "  sw-tdd-agent           TDD execution: RED -> GREEN -> REFACTOR\n"
            "  sw-reviewer-logic      Logic review: correctness + edge cases\n"
            "  sw-worktree-controller Single-task coordinator\n"
            "\n"
            "FULL: all skill directories under skills/ (excluding reports/)\n"
            "\n"
            "Agent templates (agents/*.md) are installed alongside skills for each platform."
        ),
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Install globally to user home (default: install to current directory)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="",
        metavar="PATH",
        help="Install into specific project directory (default: current dir)",
    )
    parser.add_argument(
        "--claude",
        action="store_true",
        dest="claude",
        help="Install for Claude Code (default)",
    )
    parser.add_argument(
        "--codex",
        action="store_true",
        dest="codex",
        help="Install for Codex",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Install only 4 essential skills (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen; no changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser


# ---- argument parsing ---------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.user and args.target:
        error("--user and --target are mutually exclusive.")

    if args.target:
        target = Path(args.target).resolve()
        if not target.exists():
            error(f"--target path '{args.target}' does not exist.")
        if not target.is_dir():
            error(f"--target '{args.target}' is not a directory.")
        args.target = target

    if not SOURCE_SKILLS.is_dir():
        error(f"Source skills/ not found at {SOURCE_SKILLS}")

    # Default: install to current directory when neither --user nor --target given
    if not args.user and not args.target:
        args.target = Path.cwd()

    # Default: --claude only when neither specified
    if not args.claude and not args.codex:
        args.claude = True

    return args


# ---- skill discovery ----------------------------------------------------

def get_skill_list(args: argparse.Namespace) -> list[str]:
    """Return sorted list of skill directory names to install."""
    all_skills = sorted(
        d.name
        for d in SOURCE_SKILLS.iterdir()
        if d.is_dir() and d.name != "reports"
    )

    if args.minimal:
        return sorted(s for s in all_skills if s in MINIMAL_SKILLS)

    return all_skills


# ---- platform resolution ------------------------------------------------

def get_platform_roots(args: argparse.Namespace) -> dict[str, Path]:
    """Return {platform: root_dir} dict for selected platforms."""
    roots: dict[str, Path] = {}

    active_platforms = []
    if args.claude:
        active_platforms.append(PLATFORM_CLAUDE)
    if args.codex:
        active_platforms.append(PLATFORM_CODEX)

    for plat in active_platforms:
        cfg = PLATFORM_CONFIG[plat]
        if args.user:
            root = cfg["user_skills"]
        else:
            assert args.target is not None
            root = args.target / cfg["project_skills"]
        roots[plat] = root

    return roots


# ---- confirmation -------------------------------------------------------

def confirm_or_exit(
    args: argparse.Namespace,
    skill_count: int,
    platform_roots: dict[str, Path],
) -> None:
    if args.force or args.dry_run:
        return

    agent_count = len(list(SOURCE_AGENTS.glob("*.md"))) if SOURCE_AGENTS.is_dir() else 0

    print()
    for plat, root in platform_roots.items():
        cfg = PLATFORM_CONFIG[plat]
        label = cfg["label"]
        print(f"  [{label}] {skill_count} skills -> {root}/")
        if agent_count:
            if args.user:
                agents_root = cfg["user_agents"]
            else:
                assert args.target is not None
                agents_root = args.target / cfg["project_agents"]
            print(f"  [{label}] {agent_count} agents  -> {agents_root}/")
    print()

    confirm = input("  Proceed? [y/N] ").strip().lower()
    if confirm not in ("y", "yes"):
        print("  Cancelled.")
        sys.exit(0)


# ---- install skills -----------------------------------------------------

def install_skills(
    args: argparse.Namespace,
    skill_list: list[str],
    platform_roots: dict[str, Path],
    dry_run: bool,
) -> None:
    for plat, dest_root in platform_roots.items():
        label = PLATFORM_CONFIG[plat]["label"]

        if not dry_run:
            dest_root.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[DRY-RUN] mkdir -p \"{dest_root}\"")
            continue

        count = 0
        for skill_name in skill_list:
            src = SOURCE_SKILLS / skill_name
            dst = dest_root / skill_name

            info(f"[{label}] {skill_name} ...")
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=False)
            count += 1

        success(f"[{label}] Installed {count} skill(s) to {dest_root}")

    if dry_run:
        for plat, dest_root in platform_roots.items():
            label = PLATFORM_CONFIG[plat]["label"]
            for skill_name in skill_list:
                info(f"[{label}] {skill_name} -> {dest_root / skill_name}/")


# ---- install agent templates ---------------------------------------------

def install_agent_templates(
    args: argparse.Namespace,
    platform_roots: dict[str, Path],
    dry_run: bool,
) -> None:
    """Copy agents/*.md standalone templates per platform."""
    if not SOURCE_AGENTS.is_dir():
        warn(f"agents/ not found at {SOURCE_AGENTS}; skipping agent templates.")
        return

    for plat, _skills_root in platform_roots.items():
        cfg = PLATFORM_CONFIG[plat]
        label = cfg["label"]
        if args.user:
            dest_root = cfg["user_agents"]
        else:
            assert args.target is not None
            dest_root = args.target / cfg["project_agents"]

        if dry_run:
            for agent_file in sorted(SOURCE_AGENTS.glob("*.md")):
                info(f"[{label}] {agent_file.name} -> {dest_root}/")
            continue

        dest_root.mkdir(parents=True, exist_ok=True)

        count = 0
        for agent_file in sorted(SOURCE_AGENTS.glob("*.md")):
            info(f"[{label}] {agent_file.name} ...")
            shutil.copy2(agent_file, dest_root)
            count += 1

        success(f"[{label}] Installed {count} agent template(s) to {dest_root}")


# ---- hook settings template ---------------------------------------------

HOOK_SETTINGS_TEMPLATE: dict = {
    "hooks": {
        "SessionStart": [
            {
                "matcher": "startup|clear|compact",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" session-start",
                        "async": False,
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Bash|Write|Edit|Read|Grep|Glob|Agent|TodoWrite|Skill",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" delegation-reminder",
                        "async": True,
                        "timeout": 5000,
                    }
                ],
                "description": "Remind orchestrator agents to delegate work to specialized subagents",
            },
            {
                "matcher": "Read|Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" rules-injector",
                        "async": True,
                        "timeout": 10000,
                    }
                ],
                "description": "Inject nearby project rules (AGENTS.md/CLAUDE.md) into tool output",
            },
            {
                "matcher": "Read",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" write-safety-guard-read",
                        "async": True,
                        "timeout": 3000,
                    }
                ],
                "description": "Track file reads for write-safety-guard",
            },
        ],
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" write-safety-guard",
                        "async": False,
                        "timeout": 5000,
                    }
                ],
                "description": "Block writes to existing files that haven't been read this session",
            },
            {
                "matcher": "Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 \"${workspaceFolder}/hooks/ideation-gate.py\"",
                        "async": False,
                        "timeout": 5000,
                    }
                ],
                "description": "Block delegation to implementation agents before ideation phase is complete",
            },
        ],
        "PreCompact": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${workspaceFolder}/hooks/run-hook.cmd\" hook-cleanup",
                        "async": True,
                        "timeout": 3000,
                    }
                ],
                "description": "Clear per-session hook state before context compaction",
            },
        ],
    }
}


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ---- install hooks ------------------------------------------------------

def install_hooks(
    args: argparse.Namespace,
    platform_roots: dict[str, Path],
    dry_run: bool,
) -> None:
    """Copy hooks/ directory and merge hook config into target .claude/settings.local.json."""
    source_hooks = SCRIPT_DIR / "hooks"
    if not source_hooks.is_dir():
        warn("hooks/ not found; skipping hook installation.")
        return

    # Only Claude Code supports hook installation via settings.local.json
    if not args.claude:
        return

    if args.user:
        dest_hooks = Path.home() / ".claude" / "hooks"
        settings_file = Path.home() / ".claude" / "settings.local.json"
    else:
        assert args.target is not None
        dest_hooks = args.target / "hooks"
        settings_file = args.target / ".claude" / "settings.local.json"

    if dry_run:
        info(f"[Claude Code] hooks/ -> {dest_hooks}/")
        info(f"[Claude Code] merge hook config -> {settings_file}")
        return

    # Copy hooks directory
    if dest_hooks.exists():
        shutil.rmtree(dest_hooks)
    shutil.copytree(source_hooks, dest_hooks, symlinks=False)
    info(f"[Claude Code] Installed hooks to {dest_hooks}")

    # Merge hook settings into settings.local.json
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warn(f"Could not parse {settings_file}; overwriting with fresh hook config.")
            existing = {}

    merged = deep_merge(existing, HOOK_SETTINGS_TEMPLATE)
    settings_file.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    info(f"[Claude Code] Hook config merged into {settings_file}")


# ---- summary ------------------------------------------------------------

def print_summary(
    args: argparse.Namespace,
    platform_roots: dict[str, Path],
) -> None:
    if args.dry_run:
        print()
        print("=" * 44)
        print("  DRY-RUN complete (no changes made).")
        print("  Re-run without --dry-run to install.")
        print("=" * 44)
        return

    print()
    print("=" * 44)
    print("  Installation complete")
    print("=" * 44)
    for plat, root in platform_roots.items():
        cfg = PLATFORM_CONFIG[plat]
        label = cfg["label"]
        print(f"  {label:12}  {root}")
        if SOURCE_AGENTS.is_dir():
            if args.user:
                agents_root = cfg["user_agents"]
            else:
                assert args.target is not None
                agents_root = args.target / cfg["project_agents"]
            print(f"  {label:12}  {agents_root}  (agents)")
    print()
    print("  To start using Harness:")
    for plat in platform_roots:
        label = PLATFORM_CONFIG[plat]["label"]
        hint = PLATFORM_CONFIG[plat]["invoke_hint"]
        print(f"    {label:12}  {hint}")
    print()
    print("  Tip: re-run this script anytime to update to the latest skills.")
    print("=" * 44)


# ---- main ---------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    platform_roots = get_platform_roots(args)
    skill_list = get_skill_list(args)
    dry_run = args.dry_run

    confirm_or_exit(args, len(skill_list), platform_roots)

    print()
    print("=== Installing Harness Multi-Agent Skills ===")
    print()

    install_skills(args, skill_list, platform_roots, dry_run)
    install_agent_templates(args, platform_roots, dry_run)
    install_hooks(args, platform_roots, dry_run)

    print_summary(args, platform_roots)


if __name__ == "__main__":
    main()
