from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-e2e-designer" / "SKILL.md"
PATH_DEFAULTS = ROOT / "skills" / "sw-e2e-designer" / "references" / "path-defaults.yaml"
PATH_RESOLUTION = ROOT / "skills" / "sw-e2e-designer" / "references" / "path-resolution.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_e2e_designer_declares_version_and_contract_sections() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)

    assert frontmatter["metadata"]["version"] == "2.0.0"
    dependencies = frontmatter["metadata"]["external_dependencies"]
    assert {dependency["name"] for dependency in dependencies} == {
        "sw-knowledge-agent",
        "sw-codebase-explorer",
        "sw-grill-docs",
    }
    for dependency in dependencies:
        assert dependency["version"] == "*"
        assert dependency["type"] in {"TOOL", "SKILL", "MCP"}
        assert dependency["required"] is False

    for section in (
        "## Input Contract",
        "## External Dependency Metadata",
        "## Output Contract",
        "## Acceptance Criteria",
    ):
        assert section in content


def test_e2e_paths_cover_stage_one_stage_two_and_outputs() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    defaults = yaml.safe_load(PATH_DEFAULTS.read_text(encoding="utf-8"))
    resolution = PATH_RESOLUTION.read_text(encoding="utf-8")

    assert "service_design_glob" in defaults["paths"]["evidence"]
    assert defaults["paths"]["evidence"]["service_design_glob"].endswith(
        "services/*/design.md"
    )
    artifacts = defaults["paths"]["artifact_targets"]
    assert artifacts["design_document"].endswith("/{requirement_id}/e2e/design.md")
    assert artifacts["gate_report"].endswith("/{requirement_id}/e2e/gate.md")
    assert artifacts["pre_query"].endswith("/{requirement_id}/e2e/pre-query.md")
    assert "调用方传入的 `paths`" in resolution
    assert "bundle_manifest" in resolution
    assert "Stage 1" in skill
    assert "Stage 2" in skill


def test_e2e_acceptance_covers_domain_and_case_quality() -> None:
    content = SKILL.read_text(encoding="utf-8")

    for dimension in (
        "Input and paths",
        "Dependency metadata",
        "Upstream traceability",
        "Definition integrity",
        "Journey coverage",
        "Cross-service consistency",
        "Scenario matrix",
        "Self-contained data",
        "Observable assertions",
        "Test-data safety",
        "Gate and validation",
        "Artifact and manifest",
        "Human approval and status",
    ):
        assert dimension in content


def test_e2e_preserves_stage_and_tracker_boundaries() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "every passed Stage 2 service design" in content
    assert "requirements tracker" in content
    assert "sw-controller" in content
    assert "Do not modify service designs" in content
