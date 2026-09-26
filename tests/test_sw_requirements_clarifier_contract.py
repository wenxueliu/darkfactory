from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-requirements-clarifier" / "SKILL.md"
GUIDE = ROOT / "skills" / "sw-requirements-clarifier" / "references" / "requirement-clarification.md"
PATH_DEFAULTS = ROOT / "skills" / "sw-requirements-clarifier" / "references" / "path-defaults.yaml"
PATH_RESOLUTION = ROOT / "skills" / "sw-requirements-clarifier" / "references" / "path-resolution.md"
TRACKER_GUIDE = ROOT / "skills" / "sw-requirements-clarifier" / "references" / "tracker-update.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_skill_declares_version_and_contract_sections() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)

    assert frontmatter["metadata"]["version"] == "2.2.0"
    dependencies = frontmatter["metadata"]["external_dependencies"]
    assert {dependency["name"] for dependency in dependencies} == {
        "sw-knowledge-agent",
        "sw-grill-docs",
        "sw-value-judgment",
    }
    for dependency in dependencies:
        assert dependency["version"] == "*"
        assert dependency["type"] in {"TOOL", "SKILL", "MCP"}
        assert dependency["required"] is False
    assert "## Input Contract" in content
    assert "## Output Contract" in content
    assert "## Acceptance Criteria" in content
    assert "## External Dependency Metadata" in content


def test_external_capabilities_degrade_to_skipped_without_direct_failure() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    combined = f"{skill}\n{guide}"

    assert "status: USED | SKIPPED | NOT_REQUESTED" in skill
    assert "The requirement clarification continues; this is not a direct failure." in skill
    assert "外部能力降级协议" in guide
    assert "| **SKIPPED** |" in guide
    assert "sw-knowledge-agent" in combined
    assert "sw-grill-docs" in combined
    assert "sw-value-judgment" in combined


def test_paths_are_input_overrides_with_skill_defaults() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    defaults = yaml.safe_load(PATH_DEFAULTS.read_text(encoding="utf-8"))
    resolution = PATH_RESOLUTION.read_text(encoding="utf-8")

    assert "| `paths` | No |" in skill
    assert "resolved_paths:" in skill
    assert defaults["paths"]["definition_roots"]["project"]
    assert "decision_roots" in defaults["paths"]["evidence"]
    assert "artifact_targets" in defaults["paths"]
    # tracker 是可写共享状态，必须留在只读的 evidence 命名空间之外。
    assert "tracker" not in defaults["paths"]["evidence"]
    assert "tracker" in defaults["paths"]["artifact_targets"]
    assert "调用方输入的 `paths`" in resolution
    assert "paths.artifact_targets.tracker" in TRACKER_GUIDE.read_text(encoding="utf-8")


def test_acceptance_is_multi_dimensional() -> None:
    content = SKILL.read_text(encoding="utf-8")

    for dimension in (
        "Input and paths",
        "Dependency metadata",
        "Definition integrity",
        "Business intent",
        "Scope and scenarios",
        "Functional behavior",
        "Non-functional quality",
        "Risks and dependencies",
        "Consistency and evidence",
        "Gate and validation",
        "Artifact and traceability",
        "Human approval and status",
    ):
        assert dimension in content


def test_requirement_clarifier_does_not_depend_on_external_commands() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    tracker = TRACKER_GUIDE.read_text(encoding="utf-8")

    assert "scripts/kb-search.py" not in guide
    assert "cat CONTEXT.md" not in guide
    assert "强制委托 `sw-grill-docs`" not in guide
    assert "sw-setup" not in tracker


def test_clarification_uses_complete_frontier_rounds() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")

    assert "Ask all currently unblocked, mutually independent questions in one round" in skill
    assert "决策树与 frontier 轮次提问" in guide
    assert "每轮一次提出**完整 frontier**" in guide
    assert "依赖当前 frontier 中未解决问题的后续问题必须留到下一轮" in guide
    assert "每次只问 1 个问题" not in guide
