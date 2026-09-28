#!/usr/bin/env python3
"""Initialize a Harness workspace through a short interactive interview.

The script deliberately delegates the actual installation and workspace
creation to package.py so the interactive and Agent-driven paths share the
same idempotent behavior.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import package as package_cli  # noqa: E402  (path is configured above)


PLATFORMS = {"claude", "codex", "opencode"}
DOMAINS = {"general", "fintech", "ecommerce", "internal-tools"}


def ask(prompt: str, default: str = "", choices: set[str] | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            value = input(f"{prompt}{suffix}: ").strip()
        except EOFError as exc:
            raise RuntimeError("interactive initialization requires a terminal") from exc
        value = value or default
        if not choices or value.lower() in choices:
            return value
        print(f"请输入以下选项之一：{', '.join(sorted(choices))}")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    marker = "Y/n" if default else "y/N"
    while True:
        try:
            value = input(f"{prompt} [{marker}]: ").strip().lower()
        except EOFError as exc:
            raise RuntimeError("interactive initialization requires a terminal") from exc
        if not value:
            return default
        if value in {"y", "yes", "是", "好"}:
            return True
        if value in {"n", "no", "否", "不"}:
            return False
        print("请输入 y/yes 或 n/no。")


def valid_platforms(value: str) -> bool:
    selected = {item.strip().lower() for item in value.split(",") if item.strip()}
    return bool(selected) and (selected == {"all"} or selected <= PLATFORMS)


def collect_answers(args: argparse.Namespace) -> dict[str, str | bool | None]:
    target = ask("项目目标目录", args.target or str(Path.cwd()))
    source_default = args.source or "当前 Harness 源码"
    source = ask("安装包来源（留空使用当前 Harness 源码）", source_default)
    source_value = None if source in {"当前 Harness 源码", "current", "this"} else source

    version: str | None = None
    if source_value:
        version = ask("安装包版本（latest 表示最新版）", args.version or "latest")

    platform_default = args.platform or "all"
    while True:
        platform = ask(
            "启用平台（all 或 claude,codex,opencode）",
            platform_default,
        )
        if valid_platforms(platform):
            break
        print("平台必须是 all，或由 claude/codex/opencode 组成的逗号分隔列表。")

    domain = ask("业务域", args.business_domain or "general", DOMAINS)
    language = ask("Agent 通信语言", args.language or "Chinese")
    user_name = ask("用户名称", args.user_name or getpass.getuser())
    reviewers = ask(
        "启用审核器（逗号分隔）",
        args.enabled_reviewers or "security,logic,performance",
    )
    iterations = ask(
        "多少次 AI 迭代后转人工",
        str(args.min_iteration_before_human or 3),
    )
    worktree_base = ask("worktree 目录", args.worktree_base or ".worktree")
    minimal = ask_yes_no("只安装核心 skills", args.minimal)

    answers: dict[str, str | bool | None] = {
        "target": target,
        "source": source_value,
        "version": version,
        "platform": platform,
        "business_domain": domain,
        "language": language,
        "user_name": user_name,
        "enabled_reviewers": reviewers,
        "min_iteration_before_human": iterations,
        "worktree_base": worktree_base,
        "minimal": minimal,
    }
    print("\n将执行以下初始化：")
    for key, value in answers.items():
        print(f"  {key}: {value or '(当前源码)'}")
    if not args.yes and not ask_yes_no("确认开始初始化", True):
        raise SystemExit("已取消。")
    return answers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="通过问答快速初始化 Harness 项目环境",
    )
    parser.add_argument("--target", help="预填项目目标目录")
    parser.add_argument("--source", help="预填安装包、包仓库或远程 Git 仓库")
    parser.add_argument("--version", help="预填包版本")
    parser.add_argument("--platform", help="预填平台：all、claude、codex、opencode")
    parser.add_argument("--business-domain", choices=sorted(DOMAINS))
    parser.add_argument("--language")
    parser.add_argument("--user-name")
    parser.add_argument("--enabled-reviewers")
    parser.add_argument("--min-iteration-before-human", type=int)
    parser.add_argument("--worktree-base")
    parser.add_argument("--minimal", action="store_true")
    parser.add_argument("--yes", action="store_true", help="跳过最终确认")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        answers = collect_answers(args)
        command = [
            "init",
            "--target",
            str(answers["target"]),
            "--platform",
            str(answers["platform"]),
            "--business-domain",
            str(answers["business_domain"]),
            "--language",
            str(answers["language"]),
            "--user-name",
            str(answers["user_name"]),
            "--enabled-reviewers",
            str(answers["enabled_reviewers"]),
            "--min-iteration-before-human",
            str(answers["min_iteration_before_human"]),
            "--worktree-base",
            str(answers["worktree_base"]),
        ]
        if answers["source"]:
            command.extend(["--package", str(answers["source"])])
            if answers["version"] and answers["version"] != "latest":
                command.extend(["--version", str(answers["version"])])
        if answers["minimal"]:
            command.append("--minimal")
        return package_cli.main(command)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
