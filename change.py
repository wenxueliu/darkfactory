#!/usr/bin/env python3
"""Plan and apply requirement changes across the Harness phase graph.

The planner deliberately separates impact analysis from applying the tracker
mutation.  Agents can generate and review a change packet first; only an
explicit ``apply --approve`` marks downstream artifacts as needing revision.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by installation environments
    raise RuntimeError("change.py requires PyYAML >= 6.0") from exc


PHASE_ORDER = (
    "ideation",
    "value_assessment",
    "design",
    "decomposition",
    "execution",
    "merge",
    "test",
    "delivery",
)
PHASE_ALIASES = {
    "requirements": "ideation",
    "requirements_clarification": "ideation",
    "requirements_clarifier": "ideation",
    "feature_design": "design",
    "service_design": "design",
    "e2e_design": "design",
    "task_decomposition": "decomposition",
    "plan": "decomposition",
    "coding": "execution",
    "integration_test": "test",
}
PHASE_GUIDANCE = {
    "ideation": "更新需求目标、范围、验收标准和决策记录，并重新执行需求门禁。",
    "value_assessment": "重新评估 Impact、Effort、Risk、Dependencies 和 Strategic Fit。",
    "design": "同步用户旅程、服务边界、API/事件、数据模型、失败行为和非功能约束。",
    "decomposition": "根据新设计重算任务边界、依赖 DAG、并行波次和验收测试绑定。",
    "execution": "暂停旧任务，更新受影响任务的实现说明和测试，保留已完成代码证据。",
    "merge": "重新检查分支、冲突、合并策略和合并后验证要求。",
    "test": "更新单元、API、集成和浏览器测试，并重新执行受影响门禁。",
    "delivery": "更新发布说明、验收清单、版本说明和回滚方案。",
}
TRACKER_RELATIVE_PATH = Path("knowledge/requirements-tracker.yaml")
PACKET_SCHEMA_VERSION = "1.0.0"


class ChangeError(RuntimeError):
    """Raised when a change cannot be planned or safely applied."""


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    if not normalized:
        raise ChangeError("change id cannot be empty")
    return normalized


def _load_tracker(project_root: Path) -> tuple[Path, dict[str, Any]]:
    path = project_root / TRACKER_RELATIVE_PATH
    if not path.is_file():
        raise ChangeError(f"requirements tracker does not exist: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ChangeError(f"requirements tracker is invalid: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("requirements"), (dict, list)):
        raise ChangeError("requirements tracker must contain a requirements map or list")
    return path, value


def _write_tracker(path: Path, tracker: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(tracker, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _find_requirement(tracker: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    requirements = tracker["requirements"]
    if isinstance(requirements, dict):
        item = requirements.get(requirement_id)
        if isinstance(item, dict):
            return item
    else:
        for item in requirements:
            if isinstance(item, dict) and item.get("id") == requirement_id:
                return item
    raise ChangeError(f"requirement not found in tracker: {requirement_id}")


def _append_requirement(tracker: dict[str, Any], requirement_id: str, value: dict[str, Any]) -> None:
    requirements = tracker["requirements"]
    if isinstance(requirements, dict):
        if requirement_id in requirements:
            raise ChangeError(f"requirement already exists: {requirement_id}")
        requirements[requirement_id] = value
    else:
        if any(isinstance(item, dict) and item.get("id") == requirement_id for item in requirements):
            raise ChangeError(f"requirement already exists: {requirement_id}")
        requirements.append(value)


def normalize_phase(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = PHASE_ALIASES.get(normalized, normalized)
    if normalized not in PHASE_ORDER:
        raise ChangeError(f"unknown workflow phase: {value}")
    return normalized


def _phase_revision(record: dict[str, Any], fallback: int) -> int:
    value = record.get("revision", fallback)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ChangeError(f"phase revision is not an integer: {value!r}") from exc


def _artifact_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, str):
        if value and "{" not in value and "}" not in value:
            paths.append(value)
    elif isinstance(value, list):
        for item in value:
            paths.extend(_artifact_paths(item))
    elif isinstance(value, dict):
        for item in value.values():
            paths.extend(_artifact_paths(item))
    return list(dict.fromkeys(paths))


def _parse_phase_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    values = value.split(",") if isinstance(value, str) else list(value)
    return list(dict.fromkeys(normalize_phase(item) for item in values if item.strip()))


def _new_change_id(tracker: dict[str, Any], requirement_id: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing: set[str] = set()
    requirement = _find_requirement(tracker, requirement_id)
    for item in requirement.get("change_requests", []):
        if isinstance(item, dict) and item.get("id"):
            existing.add(str(item["id"]))
    counter = 1
    while f"CHG-{date}-{counter:03d}" in existing:
        counter += 1
    return f"CHG-{date}-{counter:03d}"


def _new_requirement_id(tracker: dict[str, Any]) -> str:
    existing: set[str] = set()
    requirements = tracker["requirements"]
    items = requirements.keys() if isinstance(requirements, dict) else requirements
    for item in items:
        value = item if isinstance(requirements, dict) else item.get("id") if isinstance(item, dict) else None
        if value:
            existing.add(str(value))
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    counter = 1
    while f"REQ-{date}-{counter:03d}" in existing:
        counter += 1
    return f"REQ-{date}-{counter:03d}"


def _phase_changes(
    requirement: dict[str, Any],
    phases: list[str],
    change_summary: str,
    target_revision: int,
    strategy: str,
    project_root: Path,
) -> list[dict[str, Any]]:
    phase_records = requirement.get("phases", {})
    result: list[dict[str, Any]] = []
    for phase in phases:
        record = phase_records.get(phase, {}) if isinstance(phase_records, dict) else {}
        if not isinstance(record, dict):
            record = {}
        source_revision = _phase_revision(record, int(requirement.get("revision", 1)))
        phase_target_revision = source_revision if strategy == "edit_step" else max(source_revision + 1, target_revision)
        artifacts = _artifact_paths(record.get("artifacts", []))
        existing_artifacts = [path for path in artifacts if (project_root / path).exists()]
        result.append(
            {
                "phase": phase,
                "status_before": record.get("status", "pending"),
                "source_revision": source_revision,
                "target_revision": phase_target_revision,
                "action": "edit_step" if strategy == "edit_step" else "revise_and_validate",
                "source_artifacts": existing_artifacts,
                "declared_artifacts": artifacts,
                "content_changes": f"{PHASE_GUIDANCE[phase]}\n用户变更：{change_summary}",
                "revision_note": (
                    "仅修改当前步骤，不传播到后续阶段。"
                    if strategy == "edit_step"
                    else "旧版本保留为历史证据；完成本阶段后继续处理后续阶段。"
                ),
            }
        )
    return result


def _write_phase_deltas(packet_dir: Path, packet: dict[str, Any]) -> None:
    delta_dir = packet_dir / "phase-deltas"
    delta_dir.mkdir(parents=True, exist_ok=True)
    for index, change in enumerate(packet["phase_changes"], start=1):
        artifacts = change["source_artifacts"] or change["declared_artifacts"] or ["(not recorded)"]
        content = (
            f"# {packet['change_id']} — {change['phase']} change delta\n\n"
            f"- Requirement: `{packet['requirement_id']}`\n"
            f"- Strategy: `{packet['strategy']}`\n"
            f"- Source revision: `v{change['source_revision']}`\n"
            f"- Target revision: `v{change['target_revision']}`\n"
            f"- Status before: `{change['status_before']}`\n"
            f"- Source artifacts: {', '.join(f'`{item}`' for item in artifacts)}\n\n"
            "## Required content changes\n\n"
            f"{change['content_changes']}\n\n"
            "## Completion evidence\n\n"
            "- [ ] Revised artifact written\n"
            "- [ ] Phase gate rerun\n"
            "- [ ] Downstream handoff updated\n"
        )
        (delta_dir / f"{index:02d}-{change['phase']}.md").write_text(content, encoding="utf-8")


def propose_change(
    project_root: Path,
    requirement_id: str,
    *,
    kind: str,
    change_summary: str,
    current_phase: str | None = None,
    affected_phases: str | Iterable[str] | None = None,
    change_id: str | None = None,
    new_requirement_id: str | None = None,
) -> Path:
    """Create a reviewable change packet without mutating the tracker."""
    project_root = Path(project_root).resolve()
    tracker_path, tracker = _load_tracker(project_root)
    requirement = _find_requirement(tracker, requirement_id)
    kind = kind.strip().lower()
    if kind not in {"small", "partial", "large"}:
        raise ChangeError("kind must be small, partial, or large")
    if not change_summary.strip():
        raise ChangeError("change summary cannot be empty")

    change_id = _safe_id(change_id or _new_change_id(tracker, requirement_id))
    source_phase = normalize_phase(current_phase or requirement.get("current_phase", "ideation"))
    declared_phases = _parse_phase_list(affected_phases)
    if kind == "small":
        strategy = "edit_step"
        selected_phases = [source_phase]
        target_revision = int(requirement.get("revision", 1))
    elif kind == "partial":
        strategy = "propagate"
        start = min(
            [PHASE_ORDER.index(source_phase), *[PHASE_ORDER.index(item) for item in declared_phases]]
        )
        selected_phases = list(PHASE_ORDER[start:])
        target_revision = int(requirement.get("revision", 1)) + 1
    else:
        strategy = "new_requirement"
        selected_phases = []
        target_revision = int(requirement.get("revision", 1))

    new_requirement_id = _safe_id(new_requirement_id or _new_requirement_id(tracker)) if kind == "large" else None
    packet_dir = project_root / "knowledge" / "changes" / requirement_id / change_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    packet = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "change_id": change_id,
        "requirement_id": requirement_id,
        "kind": kind,
        "strategy": strategy,
        "source_phase": source_phase,
        "source_revision": int(requirement.get("revision", 1)),
        "target_revision": target_revision,
        "change_summary": change_summary.strip(),
        "new_requirement_id": new_requirement_id,
        "affected_phases": selected_phases,
        "phase_changes": _phase_changes(
            requirement,
            selected_phases,
            change_summary.strip(),
            target_revision,
            strategy,
            project_root,
        ),
        "tracker": str(tracker_path.relative_to(project_root)),
        "approval": {"status": "pending", "required": True},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    packet_path = packet_dir / "change-propagation.yaml"
    packet_path.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _write_phase_deltas(packet_dir, packet)
    return packet_path


def _pending_phases() -> dict[str, dict[str, Any]]:
    return {phase: {"status": "pending", "revision": 1, "artifacts": []} for phase in PHASE_ORDER}


def _append_change_request(requirement: dict[str, Any], packet: dict[str, Any], status: str) -> None:
    requirement.setdefault("change_requests", []).append(
        {
            "id": packet["change_id"],
            "kind": packet["kind"],
            "strategy": packet["strategy"],
            "summary": packet["change_summary"],
            "source_phase": packet["source_phase"],
            "affected_phases": packet["affected_phases"],
            "source_revision": packet["source_revision"],
            "target_revision": packet["target_revision"],
            "status": status,
            "packet": str(Path("knowledge") / "changes" / packet["requirement_id"] / packet["change_id"] / "change-propagation.yaml"),
            "created_at": packet["created_at"],
        }
    )


def apply_change(project_root: Path, packet_path: Path, *, approve: bool = False) -> dict[str, Any]:
    """Apply an approved packet to the tracker and mark affected outputs stale."""
    if not approve:
        raise ChangeError("apply requires explicit --approve")
    project_root = Path(project_root).resolve()
    packet_path = Path(packet_path).resolve()
    try:
        packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ChangeError(f"cannot read change packet: {packet_path}") from exc
    if not isinstance(packet, dict) or packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise ChangeError("unsupported or invalid change packet")
    tracker_path, tracker = _load_tracker(project_root)
    requirement = _find_requirement(tracker, packet["requirement_id"])
    if any(item.get("id") == packet["change_id"] for item in requirement.get("change_requests", []) if isinstance(item, dict)):
        raise ChangeError(f"change has already been applied: {packet['change_id']}")

    if packet["strategy"] == "new_requirement":
        parent = requirement
        new_id = packet["new_requirement_id"]
        if not new_id:
            raise ChangeError("new requirement change has no new_requirement_id")
        _append_requirement(
            tracker,
            new_id,
            {
                "id": new_id,
                "title": f"{parent.get('title', packet['requirement_id'])} — {packet['change_summary']}",
                "priority": parent.get("priority", "P1"),
                "revision": 1,
                "parent_requirement": packet["requirement_id"],
                "origin_change": packet["change_id"],
                "current_phase": "ideation",
                "status": "active",
                "phases": _pending_phases(),
            },
        )
        _append_change_request(requirement, packet, "accepted_new_requirement")
        result = {"status": "READY", "strategy": packet["strategy"], "new_requirement_id": new_id}
    else:
        phases = requirement.setdefault("phases", {})
        for phase_change in packet["phase_changes"]:
            phase = phase_change["phase"]
            record = phases.setdefault(phase, {})
            record["previous_status"] = record.get("status", "pending")
            record["status"] = "change_requested"
            record["revision"] = phase_change["target_revision"]
            record["superseded_by"] = packet["change_id"]
            record["change_packet"] = str(packet_path.relative_to(project_root))
        requirement["revision"] = packet["target_revision"]
        requirement["current_phase"] = packet["source_phase"]
        requirement["status"] = "active"
        _append_change_request(requirement, packet, "applied")
        result = {
            "status": "READY",
            "strategy": packet["strategy"],
            "requirement_id": packet["requirement_id"],
            "affected_phases": packet["affected_phases"],
        }
    tracker["last_change_id"] = packet["change_id"]
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_tracker(tracker_path, tracker)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="change.py", description="Propagate Harness requirement changes")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="generate a reviewable change packet")
    plan.add_argument("--project-root", type=Path, default=Path("."))
    plan.add_argument("--requirement-id", required=True)
    plan.add_argument("--kind", choices=("small", "partial", "large"), required=True)
    plan.add_argument("--change", dest="change_summary", required=True)
    plan.add_argument("--current-phase")
    plan.add_argument("--affected-phases")
    plan.add_argument("--change-id")
    plan.add_argument("--new-requirement-id")

    apply = subparsers.add_parser("apply", help="apply an approved change packet")
    apply.add_argument("--project-root", type=Path, default=Path("."))
    apply.add_argument("--packet", type=Path, required=True)
    apply.add_argument("--approve", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "plan":
            result = propose_change(
                args.project_root,
                args.requirement_id,
                kind=args.kind,
                change_summary=args.change_summary,
                current_phase=args.current_phase,
                affected_phases=args.affected_phases,
                change_id=args.change_id,
                new_requirement_id=args.new_requirement_id,
            )
            print(result)
        else:
            print(json.dumps(apply_change(args.project_root, args.packet, approve=args.approve), ensure_ascii=False, indent=2))
    except ChangeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
