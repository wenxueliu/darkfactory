from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-service-designer" / "SKILL.md"
PATH_DEFAULTS = ROOT / "skills" / "sw-service-designer" / "references" / "path-defaults.yaml"
PATH_RESOLUTION = ROOT / "skills" / "sw-service-designer" / "references" / "path-resolution.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_service_designer_declares_version_and_contract_sections() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)

    assert frontmatter["metadata"]["version"] == "2.1.0"
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
    assert "The service design continues; this is not a direct failure." in content
    assert "sw-knowledge-agent" in content
    assert "sw-codebase-explorer" in content
    assert "sw-grill-docs" in content


def test_paths_cover_upstream_bundle_and_service_artifacts() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    defaults = yaml.safe_load(PATH_DEFAULTS.read_text(encoding="utf-8"))
    resolution = PATH_RESOLUTION.read_text(encoding="utf-8")

    assert "| `paths` | No |" in skill
    assert defaults["paths"]["evidence"]["bundle_manifest"]
    assert defaults["paths"]["evidence"]["feature_design"]
    assert defaults["paths"]["evidence"]["requirement_document"]
    assert defaults["paths"]["evidence"]["requirements_gate_report"]
    artifacts = defaults["paths"]["artifact_targets"]
    assert artifacts["design_dir"].endswith("/services/{service_id}")
    assert artifacts["design_document"].endswith("/services/{service_id}/design.md")
    assert artifacts["gate_report"].endswith("/services/{service_id}/gate.md")
    assert artifacts["api_collection"].endswith("/services/{service_id}/tests/collection.json")
    assert artifacts["api_environment"].endswith("/services/{service_id}/tests/environment.json")
    assert artifacts["api_data"].endswith("/services/{service_id}/tests/data.json")
    assert artifacts["api_report"].endswith("/services/{service_id}/tests/report.xml")
    assert "调用方传入的 `paths`" in resolution
    assert "bundle_manifest" in resolution


def test_acceptance_is_multi_dimensional() -> None:
    content = SKILL.read_text(encoding="utf-8")

    for dimension in (
        "Input and paths",
        "Dependency metadata",
        "Upstream traceability",
        "Definition integrity",
        "Service evidence",
        "Technical design",
        "Interface/data contract",
        "State and failure behavior",
        "Security",
        "UT/integration tests",
        "API test artifacts",
        "Cross-service consistency",
        "Gate and validation",
        "Artifact and manifest",
        "Human approval and status",
    ):
        assert dimension in content


def test_service_designer_preserves_stage_and_service_boundaries() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "exactly one `service_id`" in content
    assert "`single_service`" in content
    assert "`cross_service_detail`" in content
    assert "a feature-design manifest" in content
    assert "ROUTE_TO_FEATURE_DESIGNER" in content
    assert "do not redesign another service" in content
    assert "Do not modify source" in content
    assert "Do not start\nE2E design or implementation from this Skill." in content
