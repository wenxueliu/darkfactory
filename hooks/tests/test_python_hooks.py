"""Behavior tests for the Python hook entry points."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path

import pytest


HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from hook_common import tool_file_paths


def load_hook(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, HOOKS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


session_start = load_hook("session-start.py", "hook_session_start")
hook_cleanup = load_hook("hook-cleanup.py", "hook_cleanup")
delegation = load_hook("delegation-reminder.py", "hook_delegation")
rules = load_hook("rules-injector.py", "hook_rules")
guard_read = load_hook("write-safety-guard-read.py", "hook_guard_read")
guard = load_hook("write-safety-guard.py", "hook_guard")


def set_stdin(monkeypatch, payload: dict):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


def test_session_start_emits_valid_claude_json(monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(HOOKS_DIR.parent))
    monkeypatch.delenv("COPILOT_CLI", raising=False)
    assert session_start.main() == 0
    output = json.loads(capsys.readouterr().out)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "using-harness" in context


def test_session_start_emits_sdk_json(monkeypatch, capsys):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("COPILOT_CLI", "1")
    assert session_start.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert "hookSpecificOutput" not in output
    assert "using-harness" in output["additionalContext"]


def test_delegation_reminds_on_third_counted_call(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(delegation, "STATE_ROOT", tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(HOOKS_DIR.parent))
    for count in range(1, 4):
        set_stdin(monkeypatch, {"session_id": "s1", "tool_name": "Read"})
        assert delegation.main() == 0
        output = capsys.readouterr().out
        if count < 3:
            assert output == ""
    parsed = json.loads(output)
    assert "3 direct tool calls" in parsed["hookSpecificOutput"]["additionalContext"]
    state = json.loads((tmp_path / "delegation-reminder" / "s1.json").read_text())
    assert state["reminderShown"] is True


def test_delegation_tool_resets_counter(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(delegation, "STATE_ROOT", tmp_path)
    set_stdin(monkeypatch, {"session_id": "s2", "tool_name": "Agent"})
    assert delegation.main() == 0
    assert capsys.readouterr().out == ""
    state = json.loads((tmp_path / "delegation-reminder" / "s2.json").read_text())
    assert state["hasDelegated"] is True
    assert state["toolCallCount"] == 0


def test_write_guard_consumes_read_permission(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    target = project / "app.py"
    target.write_text("print('ok')\n", encoding="utf-8")
    state_root = tmp_path / "state"
    monkeypatch.setattr(guard_read, "STATE_ROOT", state_root)
    monkeypatch.setattr(guard, "STATE_ROOT", state_root)
    payload = {
        "session_id": "write-session",
        "cwd": str(project),
        "tool_input": {"file_path": "app.py"},
    }
    set_stdin(monkeypatch, payload)
    assert guard_read.main() == 0
    set_stdin(monkeypatch, payload)
    assert guard.main() == 0
    assert capsys.readouterr().out == ""
    set_stdin(monkeypatch, payload)
    assert guard.main() == 2
    denied = json.loads(capsys.readouterr().out)
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_write_guard_allows_new_file(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    monkeypatch.setattr(guard, "STATE_ROOT", tmp_path / "state")
    set_stdin(monkeypatch, {
        "session_id": "s",
        "cwd": str(project),
        "tool_input": {"file_path": "new.py"},
    })
    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_codex_apply_patch_extracts_multiple_targets():
    payload = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": """*** Begin Patch
*** Update File: src/app.py
*** Add File: tests/test_app.py
*** Delete File: src/old.py
*** End Patch"""
        },
    }
    assert tool_file_paths(payload) == [
        "src/app.py", "tests/test_app.py", "src/old.py"
    ]


def test_codex_apply_patch_guard_checks_every_existing_target(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    first = project / "first.py"
    second = project / "second.py"
    first.write_text("one\n", encoding="utf-8")
    second.write_text("two\n", encoding="utf-8")
    state_root = tmp_path / "state"
    monkeypatch.setattr(guard_read, "STATE_ROOT", state_root)
    monkeypatch.setattr(guard, "STATE_ROOT", state_root)
    set_stdin(monkeypatch, {
        "session_id": "patch-session", "cwd": str(project),
        "tool_input": {"file_path": str(first)},
    })
    assert guard_read.main() == 0
    payload = {
        "session_id": "patch-session",
        "cwd": str(project),
        "tool_name": "apply_patch",
        "tool_input": {"command": """*** Begin Patch
*** Update File: first.py
*** Update File: second.py
*** End Patch"""},
    }
    set_stdin(monkeypatch, payload)
    assert guard.main() == 2
    denied = json.loads(capsys.readouterr().out)
    assert "second.py" in denied["hookSpecificOutput"]["permissionDecisionReason"]


def test_codex_contextual_patch_is_safe_without_read_event(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "app.py").write_text("old = True\n", encoding="utf-8")
    monkeypatch.setattr(guard, "STATE_ROOT", tmp_path / "state")
    set_stdin(monkeypatch, {
        "session_id": "codex-context", "cwd": str(project),
        "tool_name": "apply_patch",
        "tool_input": {"command": """*** Begin Patch
*** Update File: app.py
@@
-old = True
+old = False
*** End Patch"""},
    })
    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_rules_injector_matches_and_deduplicates(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    target = project / "app.py"
    target.write_text("pass\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("---\nalwaysApply: true\n---\nAlways test.\n", encoding="utf-8")
    monkeypatch.setattr(rules, "STATE_ROOT", tmp_path / "state")
    first = rules.build_injection(target, "rule-session")
    second = rules.build_injection(target, "rule-session")
    assert "Always test." in first
    assert second == ""


def test_rules_injector_glob_relative_to_project(tmp_path, monkeypatch):
    project = tmp_path / "project"
    source = project / "src"
    source.mkdir(parents=True)
    (project / ".git").mkdir()
    target = source / "app.py"
    target.write_text("pass\n", encoding="utf-8")
    rules_dir = project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "python.md").write_text("---\nglobs: src/*.py\n---\nPython rule.\n", encoding="utf-8")
    monkeypatch.setattr(rules, "STATE_ROOT", tmp_path / "state")
    assert "Python rule." in rules.build_injection(target, "glob-session")


def test_cleanup_removes_session_and_expired_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook_cleanup, "STATE_ROOT", tmp_path)
    current = tmp_path / "one" / "current.json"
    expired = tmp_path / "two" / "expired.json"
    fresh = tmp_path / "two" / "fresh.json"
    for path in (current, expired, fresh):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    old = 1_000_000
    os.utime(expired, (old, old))
    hook_cleanup.cleanup("current", now=old + hook_cleanup.MAX_AGE_SECONDS + 1)
    assert not current.exists()
    assert not expired.exists()
    assert fresh.exists()
    set_stdin(monkeypatch, {})
    assert hook_cleanup.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["hookEventName"] == "PreCompact"


@pytest.mark.parametrize("module", [delegation, rules, guard_read, guard])
def test_malformed_input_exits_silently(module, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))
    assert module.main() == 0
    assert capsys.readouterr().out == ""
