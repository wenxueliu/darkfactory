from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

SKILLS = {
    "sw-task-decomposer": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-plan-executor": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-finishing-branch": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-integration-tester": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-browser-tester": {
        "version": "3.0.0",
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": (
            "path-defaults.yaml",
            "path-resolution.md",
            "webbridge-test-template.md",
            "webbridge-evidence-strategy.md",
            "webbridge-visual-evidence.md",
        ),
    },
    "sw-strategic-planner": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-grill-docs": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
    },
    "sw-value-judgment": {
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": (
            "path-defaults.yaml",
            "path-resolution.md",
            "value-assessment.md",
            "roi-evaluation.md",
            "priority-ranking.md",
        ),
    },
}


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_downstream_skills_declare_v2_contracts_and_dependencies() -> None:
    for name, contract in SKILLS.items():
        skill_dir = ROOT / "skills" / name
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = _frontmatter(content)

        assert frontmatter["metadata"]["version"] == contract.get("version", "2.0.0")
        dependencies = frontmatter["metadata"]["external_dependencies"]
        assert dependencies
        for dependency in dependencies:
            assert {
                "name",
                "version",
                "type",
                "required",
                "purpose",
            } <= dependency.keys()
            assert dependency["type"] in {"TOOL", "SKILL", "MCP"}
            assert isinstance(dependency["required"], bool)

        for section in contract["required_sections"]:
            assert section in content
        for reference in contract["required_refs"]:
            assert (skill_dir / "references" / reference).exists()
        assert "semantic paths" in content.lower()


def test_task_and_execution_handoff_contracts_are_explicit() -> None:
    task = (ROOT / "skills/sw-task-decomposer/SKILL.md").read_text(encoding="utf-8")
    executor = (ROOT / "skills/sw-plan-executor/SKILL.md").read_text(encoding="utf-8")

    assert "manifest status is `complete`" in task
    assert "`sw-plan-executor`" in task
    assert "never writes product code" in executor
    assert "Final Verification Wave" in executor
    assert "`sw-finishing-branch`" in executor


def test_terminal_and_test_skills_keep_stage_boundaries() -> None:
    finishing = (ROOT / "skills/sw-finishing-branch/SKILL.md").read_text(encoding="utf-8")
    integration = (ROOT / "skills/sw-integration-tester/SKILL.md").read_text(encoding="utf-8")
    browser = (ROOT / "skills/sw-browser-tester/SKILL.md").read_text(encoding="utf-8")
    planner = (ROOT / "skills/sw-strategic-planner/SKILL.md").read_text(encoding="utf-8")

    assert "Exactly four choices" in finishing
    assert "exact text `discard`" in finishing
    assert "`newman` and `python3` are mandatory" in integration
    assert "must never be silently skipped" in integration
    assert "API-only cases belong to `sw-integration-tester`" in browser
    assert "real browser" in browser
    assert "kimi-webbridge" in browser
    assert "Do not generate local test-script files" in browser
    assert "sw-pre-planning-consultant" in planner
    assert "exactly one executable plan" in planner
    assert "The interview state is runtime context" in planner


def test_browser_contract_has_no_playwright_dependency_or_artifact() -> None:
    browser = (ROOT / "skills/sw-browser-tester/SKILL.md").read_text(encoding="utf-8")
    defaults = yaml.safe_load(
        (ROOT / "skills/sw-browser-tester/references/path-defaults.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "playwright" not in browser.lower()
    assert "kimi-webbridge" in browser
    artifacts = defaults["paths"]["artifact_targets"]
    assert artifacts["session_log"].endswith("browser-e2e-session.json")
    assert "test_script" not in artifacts


def test_path_defaults_are_valid_yaml_and_have_artifact_targets() -> None:
    for name in SKILLS:
        defaults = yaml.safe_load(
            (ROOT / "skills" / name / "references/path-defaults.yaml").read_text(
                encoding="utf-8"
            )
        )
        paths = defaults["paths"]
        assert paths["config_file"]
        if "evidence" in paths:
            assert paths["evidence"]
        else:
            assert paths.get("context_files") or paths.get("context_maps")
        assert paths.get("artifact_targets") or paths.get("write_targets")


def test_value_artifacts_are_requirement_cohesive() -> None:
    value_defaults = yaml.safe_load(
        (ROOT / "skills/sw-value-judgment/references/path-defaults.yaml").read_text(
            encoding="utf-8"
        )
    )
    clarifier_defaults = yaml.safe_load(
        (
            ROOT
            / "skills/sw-requirements-clarifier/references/path-defaults.yaml"
        ).read_text(encoding="utf-8")
    )

    value_targets = value_defaults["paths"]["artifact_targets"]
    clarifier_targets = clarifier_defaults["paths"]["artifact_targets"]
    assert value_targets["requirement_document"] == (
        "knowledge/requirements/{requirement_id}/requirement.md"
    )
    assert value_targets["value_assessment"] == (
        "knowledge/requirements/{requirement_id}/value-assessment.md"
    )
    assert value_targets["roi"] == "knowledge/requirements/{requirement_id}/roi.md"
    assert clarifier_targets["value_assessment"] == value_targets["value_assessment"]
    assert value_targets["priority_ranking"].startswith(
        "knowledge/value-assessment/"
    )
