from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("harness_change", ROOT / "change.py")
assert SPEC is not None and SPEC.loader is not None
change = importlib.util.module_from_spec(SPEC)
sys.modules["harness_change"] = change
SPEC.loader.exec_module(change)


def _workspace(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "knowledge" / "designs" / "REQ-001").mkdir(parents=True)
    (project / "knowledge" / "tasks").mkdir(parents=True)
    (project / "knowledge" / "requirements").mkdir(parents=True)
    (project / "knowledge" / "requirements-tracker.yaml").write_text(
        yaml.safe_dump(
            {
                "requirements": [
                    {
                        "id": "REQ-001",
                        "title": "Demo requirement",
                        "priority": "P1",
                        "revision": 1,
                        "current_phase": "design",
                        "status": "active",
                        "phases": {
                            "ideation": {"status": "done", "revision": 1},
                            "design": {
                                "status": "done",
                                "revision": 1,
                                "artifacts": [
                                    "knowledge/designs/REQ-001/feature-design.md"
                                ],
                            },
                            "decomposition": {"status": "done", "revision": 1},
                            "execution": {"status": "in_progress", "revision": 1},
                            "merge": {"status": "pending", "revision": 1},
                            "test": {"status": "pending", "revision": 1},
                            "delivery": {"status": "pending", "revision": 1},
                        },
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project / "knowledge" / "designs" / "REQ-001" / "feature-design.md").write_text(
        "# Feature design v1\n", encoding="utf-8"
    )
    return project


def test_partial_change_generates_current_and_downstream_revisions(tmp_path: Path) -> None:
    project = _workspace(tmp_path)

    packet_path = change.propose_change(
        project,
        "REQ-001",
        kind="partial",
        change_summary="增加权限校验",
        current_phase="design",
        change_id="CHG-001",
    )

    packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))
    assert packet["strategy"] == "propagate"
    assert packet["target_revision"] == 2
    assert packet["affected_phases"] == [
        "design",
        "decomposition",
        "execution",
        "merge",
        "test",
        "delivery",
    ]
    assert packet["phase_changes"][0]["source_revision"] == 1
    assert packet["phase_changes"][0]["target_revision"] == 2
    assert "增加权限校验" in packet["phase_changes"][2]["content_changes"]
    assert (packet_path.parent / "phase-deltas" / "01-design.md").is_file()
    assert (packet_path.parent / "phase-deltas" / "06-delivery.md").is_file()


def test_apply_partial_change_marks_completed_downstream_stale(tmp_path: Path) -> None:
    project = _workspace(tmp_path)
    packet_path = change.propose_change(
        project,
        "REQ-001",
        kind="partial",
        change_summary="增加权限校验",
        current_phase="design",
        change_id="CHG-002",
    )

    change.apply_change(project, packet_path, approve=True)
    tracker = yaml.safe_load(
        (project / "knowledge" / "requirements-tracker.yaml").read_text(encoding="utf-8")
    )
    requirement = tracker["requirements"][0]
    assert requirement["revision"] == 2
    assert requirement["current_phase"] == "design"
    assert requirement["phases"]["design"]["status"] == "change_requested"
    assert requirement["phases"]["decomposition"]["status"] == "change_requested"
    assert requirement["phases"]["decomposition"]["superseded_by"] == "CHG-002"
    assert requirement["change_requests"][0]["id"] == "CHG-002"


def test_small_change_only_updates_one_step(tmp_path: Path) -> None:
    project = _workspace(tmp_path)
    packet_path = change.propose_change(
        project,
        "REQ-001",
        kind="small",
        change_summary="修正字段校验提示",
        current_phase="execution",
        change_id="CHG-003",
    )
    packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))

    assert packet["strategy"] == "edit_step"
    assert packet["affected_phases"] == ["execution"]
    assert packet["phase_changes"][0]["source_revision"] == 1
    assert packet["phase_changes"][0]["target_revision"] == 1


def test_large_change_creates_new_requirement_without_propagating_old_one(tmp_path: Path) -> None:
    project = _workspace(tmp_path)
    packet_path = change.propose_change(
        project,
        "REQ-001",
        kind="large",
        change_summary="改为多租户权限模型",
        current_phase="execution",
        change_id="CHG-004",
        new_requirement_id="REQ-002",
    )
    packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))

    assert packet["strategy"] == "new_requirement"
    assert packet["new_requirement_id"] == "REQ-002"
    assert packet["affected_phases"] == []

    change.apply_change(project, packet_path, approve=True)
    tracker = yaml.safe_load(
        (project / "knowledge" / "requirements-tracker.yaml").read_text(encoding="utf-8")
    )
    assert [item["id"] for item in tracker["requirements"]] == ["REQ-001", "REQ-002"]
    assert tracker["requirements"][1]["current_phase"] == "ideation"
