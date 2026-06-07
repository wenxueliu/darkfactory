"""Tests for hooks/session-end-check.py — leftover work detection.

Run with:
    cd /home/chengnanfeng/code/harness/services/multiagents/hooks
    python3 -m pytest tests/test_session_end_check.py -v
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "session_end_check", HOOKS_DIR / "session-end-check.py"
)
sec = importlib.util.module_from_spec(_spec)
sys.modules["session_end_check"] = sec
_spec.loader.exec_module(sec)


# --- scan_in_progress_tasks ---

def test_scan_in_progress_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = sec.scan_in_progress_tasks(str(tmp_path))
    assert result == []


def test_scan_in_progress_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "tasks.yaml").write_text("""
tasks:
  - id: TASK-1
    title: "Fix login"
    status: in_progress
  - id: TASK-2
    title: "Add logout"
    status: done
""", encoding="utf-8")
    result = sec.scan_in_progress_tasks(str(tmp_path))
    assert len(result) == 1
    assert result[0]["id"] == "TASK-1"
    assert "Fix login" in result[0]["title"]


def test_scan_in_progress_yaml_multiple(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "tasks.yaml").write_text("""
tasks:
  - id: TASK-A
    status: in_progress
  - id: TASK-B
    status: in_progress
  - id: TASK-C
    status: done
""", encoding="utf-8")
    result = sec.scan_in_progress_tasks(str(tmp_path))
    assert len(result) == 2
    assert {r["id"] for r in result} == {"TASK-A", "TASK-B"}


# --- scan_worktrees ---

def test_scan_worktrees_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = sec.scan_worktrees(str(tmp_path))
    assert result == []


# --- build_warning ---

def test_build_warning_no_data():
    msg = sec.build_warning([], [])
    assert "Leftover state detected" in msg
    assert "sw-finishing-branch" in msg  # recommendation is always present
    # When both lists are empty, no per-category lines
    assert "0 in_progress" not in msg
    assert "0 worktree" not in msg


def test_build_warning_with_in_progress():
    msg = sec.build_warning([{"id": "TASK-1", "title": "Fix bug"}], [])
    assert "TASK-1" in msg
    assert "1 in_progress" in msg


def test_build_warning_with_worktrees():
    msg = sec.build_warning([], [{"name": "wt-1", "path": "/tmp", "dirty_files": 3}])
    assert "wt-1" in msg
    assert "3 files" in msg


def test_build_warning_with_both():
    msg = sec.build_warning(
        [{"id": "T1", "title": ""}],
        [{"name": "wt-1", "path": "/x", "dirty_files": 5}],
    )
    assert "T1" in msg
    assert "wt-1" in msg


# --- main() end-to-end ---

def test_main_clean_state_exits_silently(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # No tasks file, no worktree dir → exit 0 silently
    input_data = {"cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        sec.main()
    assert exc_info.value.code == 0
    assert capsys.readouterr().out == ""


def test_main_in_progress_emits_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "tasks.yaml").write_text("""
tasks:
  - id: T-WIP
    status: in_progress
""", encoding="utf-8")
    input_data = {"cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        sec.main()
    out = capsys.readouterr().out
    assert exc_info.value.code == 0  # always 0 (warning, not deny)
    assert "Leftover state" in out
    assert "T-WIP" in out
    assert "SessionEnd" in out
