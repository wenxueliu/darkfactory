from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HOOKS = Path(__file__).resolve().parents[1]


def load_script(name: str):
    module_name = name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_work(root: Path, execution_state: str = "running") -> None:
    works = root / ".works"
    (works / "inbox").mkdir(parents=True)
    (works / "state.json").write_text(json.dumps({
        "version": 6,
        "execution_state": execution_state,
        "completed": execution_state == "completed",
        "pending_feedback": [],
        "awaiting_route": False,
    }), encoding="utf-8")


def set_stdin(monkeypatch, payload: dict) -> None:
    value = json.dumps(payload)
    monkeypatch.setattr(sys, "stdin", type("Input", (), {
        "read": lambda self: value,
    })())


def test_user_prompt_is_atomically_ingested_for_active_work(tmp_path, monkeypatch, capsys):
    make_work(tmp_path)
    hook = load_script("works-feedback-ingest")
    set_stdin(monkeypatch, {
        "session_id": "session-1", "cwd": str(tmp_path),
        "prompt": "这里的状态转换不对，先检查一下",
    })

    assert hook.main() == 0

    files = list((tmp_path / ".works" / "inbox").glob("HF-*.json"))
    assert len(files) == 1
    feedback = json.loads(files[0].read_text(encoding="utf-8"))
    assert feedback["kind"] == "message"
    assert feedback["status"] == "delivered"
    assert feedback["source"]["host_event"] == "UserPromptSubmit"
    output = json.loads(capsys.readouterr().out)
    assert "works next" in output["hookSpecificOutput"]["additionalContext"]


def test_explicit_pause_and_resume_are_hard_control_events(tmp_path, monkeypatch, capsys):
    make_work(tmp_path)
    hook = load_script("works-feedback-ingest")
    for prompt, action in (("立即停止，不要继续", "pause"), ("继续执行", "resume")):
        set_stdin(monkeypatch, {
            "session_id": f"session-{action}", "cwd": str(tmp_path), "prompt": prompt,
        })
        assert hook.main() == 0
        capsys.readouterr()
    rows = [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((tmp_path / ".works" / "inbox").glob("HF-*.json"))]
    assert {(row["kind"], row.get("action")) for row in rows} == {
        ("control", "pause"), ("control", "resume"),
    }


def test_prompt_hook_is_silent_without_active_work(tmp_path, monkeypatch, capsys):
    hook = load_script("works-feedback-ingest")
    set_stdin(monkeypatch, {"cwd": str(tmp_path), "prompt": "继续"})
    assert hook.main() == 0
    assert capsys.readouterr().out == ""


def test_pre_tool_guard_blocks_business_tool_until_feedback_is_processed(
    tmp_path, monkeypatch, capsys,
):
    make_work(tmp_path)
    inbox = tmp_path / ".works" / "inbox" / "HF-1.json"
    inbox.write_text(json.dumps({
        "id": "HF-1", "kind": "message", "message": "wait",
        "status": "delivered", "created_at": 1,
    }), encoding="utf-8")
    hook = load_script("works-next-guard")
    set_stdin(monkeypatch, {
        "session_id": "s", "cwd": str(tmp_path), "tool_name": "Read",
        "tool_input": {"file_path": "README.md"},
    })

    assert hook.main() == 2
    output = json.loads(capsys.readouterr().out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "works next" in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_pre_tool_guard_allows_works_control_commands(tmp_path, monkeypatch, capsys):
    make_work(tmp_path)
    (tmp_path / ".works" / "inbox" / "HF-1.json").write_text(json.dumps({
        "id": "HF-1", "kind": "message", "message": "wait",
        "status": "delivered", "created_at": 1,
    }), encoding="utf-8")
    hook = load_script("works-next-guard")
    set_stdin(monkeypatch, {
        "session_id": "s", "cwd": str(tmp_path), "tool_name": "Bash",
        "tool_input": {"command": "python skills/works/scripts/works.py --project . next"},
    })

    assert hook.main() == 0
    assert capsys.readouterr().out == ""


def test_post_tool_boundary_injects_pending_feedback_reminder(tmp_path, monkeypatch, capsys):
    make_work(tmp_path)
    (tmp_path / ".works" / "inbox" / "HF-1.json").write_text(json.dumps({
        "id": "HF-1", "kind": "message", "message": "wait",
        "status": "delivered", "created_at": 1,
    }), encoding="utf-8")
    hook = load_script("works-boundary")
    set_stdin(monkeypatch, {"cwd": str(tmp_path), "tool_name": "Read"})

    assert hook.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert "HF-1" in output["hookSpecificOutput"]["additionalContext"]
