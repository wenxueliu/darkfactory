"""Tests for standalone Codex hook installation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("multiagents_install", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
sys.modules["multiagents_install"] = installer
assert spec.loader is not None
spec.loader.exec_module(installer)


def args_for(target: Path) -> argparse.Namespace:
    return argparse.Namespace(
        user=False,
        target=target,
        claude=False,
        codex=True,
        dry_run=False,
    )


def claude_args_for(target: Path) -> argparse.Namespace:
    return argparse.Namespace(
        user=False,
        target=target,
        claude=True,
        codex=False,
        dry_run=False,
    )


def test_codex_install_writes_scripts_and_config(tmp_path):
    installer.install_hooks(args_for(tmp_path), {}, False)
    codex_root = tmp_path / ".codex"
    config_path = codex_root / "hooks.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert (codex_root / "hooks" / "ideation-gate.py").is_file()
    assert (codex_root / "hooks" / "works-feedback-ingest.py").is_file()
    assert (codex_root / "hooks" / "works-next-guard.py").is_file()
    assert not (codex_root / "hooks" / "tests").exists()
    assert not list((tmp_path / ".agents" / "skills").glob("*-agent.md"))
    pretool = config["hooks"]["PreToolUse"]
    assert any("apply_patch" in group["matcher"] for group in pretool)
    handlers = [handler for group in pretool for handler in group["hooks"]]
    assert all("commandWindows" in handler for handler in handlers)
    assert all(".codex/hooks/" in handler["command"] for handler in handlers)
    prompt_commands = [
        handler["command"]
        for group in config["hooks"]["UserPromptSubmit"]
        for handler in group["hooks"]
    ]
    assert any("works-feedback-ingest.py" in command for command in prompt_commands)
    assert all(handler.get("timeout", 0) <= 10 for handler in handlers)


def test_codex_install_preserves_unrelated_hooks_and_is_idempotent(tmp_path):
    codex_root = tmp_path / ".codex"
    codex_root.mkdir()
    custom = {
        "hooks": {
            "SessionStart": [{
                "matcher": "startup",
                "hooks": [{"type": "command", "command": "python3 custom.py"}],
            }]
        }
    }
    (codex_root / "hooks.json").write_text(json.dumps(custom), encoding="utf-8")
    args = args_for(tmp_path)
    installer.install_hooks(args, {}, False)
    installer.install_hooks(args, {}, False)
    config = json.loads((codex_root / "hooks.json").read_text(encoding="utf-8"))
    groups = config["hooks"]["SessionStart"]
    commands = [handler["command"] for group in groups for handler in group["hooks"]]
    assert commands.count("python3 custom.py") == 1
    assert sum("session-start.py" in command for command in commands) == 1


def test_claude_install_enables_works_feedback_boundaries(tmp_path):
    installer.install_hooks(claude_args_for(tmp_path), {}, False)
    settings = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    prompt_commands = [
        handler["command"]
        for group in settings["hooks"]["UserPromptSubmit"]
        for handler in group["hooks"]
    ]
    pre_commands = [
        handler["command"]
        for group in settings["hooks"]["PreToolUse"]
        for handler in group["hooks"]
    ]
    post_commands = [
        handler["command"]
        for group in settings["hooks"]["PostToolUse"]
        for handler in group["hooks"]
    ]
    assert any("works-feedback-ingest.py" in command for command in prompt_commands)
    assert any("works-next-guard.py" in command for command in pre_commands)
    assert any("works-boundary.py" in command for command in post_commands)
