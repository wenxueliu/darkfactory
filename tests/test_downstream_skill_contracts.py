from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

SKILLS = {
    "sw-task-decomposer": {
        "version": "2.2.0",
        "required_sections": (
            "## Input Contract",
            "## External Dependency Metadata",
            "## Output Contract",
            "## Acceptance Criteria",
        ),
        "required_refs": (
            "path-defaults.yaml",
            "path-resolution.md",
            "minimal-execution-plan.md",
        ),
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
        "version": "2.1.0",
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
    assert "`single_service`" in task
    assert "does not invent an E2E task" in task
    assert "minimal execution plan" in task
    assert "plan_path" in task
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
    assert "approved requirement and design bundle" in planner
    assert "does not introduce new feature/service design decisions" in planner
    assert "sw-task-decomposer" in planner


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


def test_integration_results_are_requirement_cohesive() -> None:
    defaults = yaml.safe_load(
        (
            ROOT
            / "skills/sw-integration-tester/references/path-defaults.yaml"
        ).read_text(encoding="utf-8")
    )
    target = defaults["paths"]["artifact_targets"]["test_results"]
    assert target == "knowledge/requirements/{requirement_id}/test-results.yaml"
    assert defaults["paths"]["evidence"]["integration_plan"] == (
        "knowledge/requirements/{requirement_id}/integration-test-plan.md"
    )
    runner = (
        ROOT / "skills/sw-integration-tester/scripts/newman_runner.py"
    ).read_text(encoding="utf-8")
    assert '"requirements"' in runner
    assert '"results_yaml"' in runner


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


def test_every_skill_declares_the_common_contract() -> None:
    skill_files = sorted((ROOT / "skills").glob("*/SKILL.md"))
    assert len(skill_files) == 44

    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = _frontmatter(content)
        metadata = frontmatter.get("metadata")

        assert frontmatter["name"] == skill_file.parent.name
        assert isinstance(metadata, dict)
        assert isinstance(metadata.get("version"), str)
        assert metadata["version"]
        assert isinstance(metadata.get("external_dependencies"), list)
        for dependency in metadata["external_dependencies"]:
            assert {
                "name",
                "version",
                "type",
                "required",
                "purpose",
            } <= dependency.keys()
            assert dependency["type"] in {"TOOL", "SKILL", "MCP", "LIBRARY"}
            assert isinstance(dependency["required"], bool)

        if metadata["external_dependencies"]:
            assert "## External Dependency Metadata" in content

        assert "## Input Contract" in content
        assert "## Output Contract" in content
        assert "## Acceptance Criteria" in content


def test_workflow_artifacts_stay_under_knowledge() -> None:
    scanned = [ROOT / "package.py"]
    scanned.extend((ROOT / "docs").rglob("*.md"))
    scanned.extend((ROOT / "skills").rglob("*.md"))
    scanned.extend((ROOT / "skills").rglob("*.yaml"))

    offenders = []
    for path in scanned:
        if "__pycache__" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if "_context-output" in content:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []
