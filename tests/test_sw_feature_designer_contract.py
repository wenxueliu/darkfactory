from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-feature-designer" / "SKILL.md"
PATH_DEFAULTS = ROOT / "skills" / "sw-feature-designer" / "references" / "path-defaults.yaml"
PATH_RESOLUTION = ROOT / "skills" / "sw-feature-designer" / "references" / "path-resolution.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_feature_designer_declares_version_and_contract_sections() -> None:
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


def test_optional_dependencies_degrade_without_direct_failure() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "status: USED | SKIPPED | NOT_REQUESTED" in content
    assert "The feature design continues; this is not a direct failure." in content
    assert "sw-knowledge-agent" in content
    assert "sw-codebase-explorer" in content
    assert "sw-grill-docs" in content


def test_paths_are_semantic_overrides_with_writable_artifact_targets() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    defaults = yaml.safe_load(PATH_DEFAULTS.read_text(encoding="utf-8"))
    resolution = PATH_RESOLUTION.read_text(encoding="utf-8")

    assert "| `paths` | No |" in skill
    assert defaults["paths"]["definition_roots"]["project"]
    assert defaults["paths"]["evidence"]["service_registry"]
    artifacts = defaults["paths"]["artifact_targets"]
    assert artifacts["design_dir"].endswith("knowledge/designs/{requirement_id}")
    assert artifacts["design_document"].endswith("/{requirement_id}/feature-design.md")
    assert artifacts["manifest"].endswith("/{requirement_id}/manifest.yaml")
    assert artifacts["service_design_dir"].endswith("/{requirement_id}/services")
    assert artifacts["e2e_design"].endswith("/{requirement_id}/e2e/design.md")
    assert "调用方传入的 `paths`" in resolution
    assert "tracker" in defaults["paths"]["artifact_targets"]


def test_output_and_validation_contract_is_multi_dimensional() -> None:
    content = SKILL.read_text(encoding="utf-8")

    for dimension in (
        "Input and paths",
        "Dependency metadata",
        "Upstream traceability",
        "Definition integrity",
        "Knowledge evidence",
        "Service impact",
        "User journey",
        "Interaction quality",
        "Contract clarity",
        "Deployment readiness",
        "Consistency and review",
        "Gate and validation",
        "Artifact and tracker",
        "Human approval and status",
    ):
        assert dimension in content


def test_feature_designer_preserves_stage_boundaries() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "Do not design the internal implementation of an individual service" in content
    assert "Then hand the resolved design document to `sw-service-designer`" in content
    assert "Do not begin\nservice implementation from this Skill." in content
