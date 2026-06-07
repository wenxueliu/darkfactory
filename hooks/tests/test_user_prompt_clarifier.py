"""Tests for hooks/user-prompt-clarifier.py — soft hint logic.

Run with:
    cd /home/chengnanfeng/code/harness/services/multiagents/hooks
    python3 -m pytest tests/test_user_prompt_clarifier.py -v
"""
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "user_prompt_clarifier", HOOKS_DIR / "user-prompt-clarifier.py"
)
upc = importlib.util.module_from_spec(_spec)
sys.modules["user_prompt_clarifier"] = upc
_spec.loader.exec_module(upc)


# --- Implementation verb detection ---

def test_detect_chinese_implement_verb():
    assert upc.IMPLEMENTATION_VERBS.search("帮我实现一个登录功能") is not None


def test_detect_english_implement_verb():
    assert upc.IMPLEMENTATION_VERBS.search("Please add a new feature") is not None


def test_no_match_for_question():
    assert upc.IMPLEMENTATION_VERBS.search("怎么用这个工具?") is None


def test_no_match_for_exploration():
    assert upc.IMPLEMENTATION_VERBS.search("看看用户表的 schema") is None


# --- Follow-up / skip detection ---

def test_followup_continue_chinese():
    assert upc.FOLLOWUP_TOKENS.search("接着刚才的修改") is not None


def test_followup_continue_english():
    assert upc.FOLLOWUP_TOKENS.search("continue with the next step") is not None


def test_explicit_skip():
    assert upc.EXPLICIT_SKIP.search("直接做就行") is not None
    assert upc.EXPLICIT_SKIP.search("skip clarification") is not None


# --- read_tracker_status ---

def test_read_tracker_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    status = upc.read_tracker_status(str(tmp_path))
    assert status["exists"] is False
    assert status["has_in_progress"] is False


def test_read_tracker_with_in_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-001
    status: in_progress
  - id: REQ-002
    status: done
""", encoding="utf-8")
    status = upc.read_tracker_status(str(tmp_path))
    assert status["exists"] is True
    assert status["has_in_progress"] is True
    assert "REQ-001" in status["in_progress_ids"]


def test_read_tracker_no_in_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-002
    status: done
""", encoding="utf-8")
    status = upc.read_tracker_status(str(tmp_path))
    assert status["has_in_progress"] is False


def test_read_tracker_malformed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "requirements-tracker.yaml").write_text("not: valid: yaml: ::", encoding="utf-8")
    status = upc.read_tracker_status(str(tmp_path))
    assert status["exists"] is True
    assert status["parse_error"] is not None


# --- build_hint ---

def test_build_hint_no_tracker():
    status = {"exists": False, "has_in_progress": False, "in_progress_ids": [],
              "parse_error": None}
    hint = upc.build_hint(status, "实现登录")
    assert "No requirements-tracker.yaml" in hint
    assert "sw-requirements-clarifier" in hint


def test_build_hint_with_in_progress():
    status = {"exists": True, "has_in_progress": True, "in_progress_ids": ["REQ-1"],
              "parse_error": None}
    hint = upc.build_hint(status, "实现登录")
    assert "Active requirements" in hint
    assert "REQ-1" in hint


def test_build_hint_no_in_progress():
    status = {"exists": True, "has_in_progress": False, "in_progress_ids": [],
              "parse_error": None}
    hint = upc.build_hint(status, "实现登录")
    assert "no in-progress" in hint


# --- main() end-to-end via stdin ---

def test_main_no_implementation_verb_exits_silently(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    input_data = {"prompt": "看看这个文件是干嘛的", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        upc.main()
    assert exc_info.value.code == 0
    assert capsys.readouterr().out == ""


def test_main_implementation_no_tracker_emits_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    input_data = {"prompt": "实现一个登录接口", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        upc.main()
    out = capsys.readouterr().out
    assert exc_info.value.code == 0  # always exit 0 (soft hint)
    assert "sw-requirements-clarifier" in out
    assert "UserPromptSubmit" in out


def test_main_explicit_skip_exits_silently(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    input_data = {"prompt": "直接做就行", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        upc.main()
    assert exc_info.value.code == 0
    assert capsys.readouterr().out == ""


def test_main_followup_with_in_progress_skips(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "_context" / "memory" / "sw-shared"
    kb_dir.mkdir(parents=True)
    (kb_dir / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-001
    status: in_progress
""", encoding="utf-8")
    input_data = {"prompt": "继续刚才的实现", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: json.dumps(input_data)})())
    with pytest.raises(SystemExit) as exc_info:
        upc.main()
    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    # Followup with in-progress → minimal hint with active list
    assert "Active requirements" in out
