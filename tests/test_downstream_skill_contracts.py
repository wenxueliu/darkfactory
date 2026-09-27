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
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": ("path-defaults.yaml", "path-resolution.md"),
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
}


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_downstream_skills_declare_v2_contracts_and_dependencies() -> None:
    for name, contract in SKILLS.items():
        skill_dir = ROOT / "skills" / name
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = _frontmatter(content)

        assert frontmatter["metadata"]["version"] == "2.0.0"
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
    assert "sw-pre-planning-consultant" in planner
    assert "exactly one executable plan" in planner
    assert "The interview state is runtime context" in planner


def test_path_defaults_are_valid_yaml_and_have_artifact_targets() -> None:
    for name in SKILLS:
        defaults = yaml.safe_load(
            (ROOT / "skills" / name / "references/path-defaults.yaml").read_text(
                encoding="utf-8"
            )
        )
        paths = defaults["paths"]
        assert paths["config_file"]
        assert paths["evidence"]
        assert paths["artifact_targets"]
