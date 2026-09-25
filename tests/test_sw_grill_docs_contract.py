from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-grill-docs" / "SKILL.md"
CHECKLIST = ROOT / "skills" / "sw-grill-docs" / "references" / "grill-checklist.md"
PATH_DEFAULTS = ROOT / "skills" / "sw-grill-docs" / "references" / "path-defaults.yaml"
PATH_RESOLUTION = ROOT / "skills" / "sw-grill-docs" / "references" / "path-resolution.md"
WORKSPACE_PATHS = ROOT / "docs" / "workspace-paths.md"
CALLERS = (
    ROOT / "skills" / "sw-brainstorming" / "SKILL.md",
    ROOT / "skills" / "sw-strategic-planner" / "SKILL.md",
)


def _frontmatter_description(text: str) -> str:
    frontmatter = text.split("---", 2)[1]
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise AssertionError("sw-grill-docs must declare a description")


def test_sw_grill_docs_description_only_routes_matching_requests() -> None:
    description = _frontmatter_description(SKILL.read_text(encoding="utf-8"))

    assert description.startswith("Use when")
    assert "updates documentation inline" not in description
    assert "trigger:" in description


def test_sw_grill_docs_discovers_all_supported_decision_sources() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    defaults = PATH_DEFAULTS.read_text(encoding="utf-8")

    assert "references/path-defaults.yaml" in skill
    for semantic_path in ("context_files", "context_maps", "decision_roots", "source_roots", "config_file"):
        assert semantic_path in skill
        assert semantic_path in defaults
    assert "write_targets" in defaults
    assert "读取路径和写入路径分离" in skill
    resolution = PATH_RESOLUTION.read_text(encoding="utf-8")
    assert "path-defaults.yaml" in resolution
    assert "write_targets" in resolution
    assert "workflow_root" in resolution
    workspace_paths = WORKSPACE_PATHS.read_text(encoding="utf-8")
    assert "decision_roots" in workspace_paths
    assert "write_targets" in workspace_paths


def test_sw_grill_docs_preserves_caller_contracts() -> None:
    skill = SKILL.read_text(encoding="utf-8")

    assert "PASS" in skill
    assert "CONCERNS" in skill
    assert "CONFLICT" in skill
    assert "调用方负责" in skill or "caller" in skill

    for path in CALLERS + (
        ROOT / "skills" / "sw-requirements-clarifier" / "references" / "requirement-clarification.md",
    ):
        content = path.read_text(encoding="utf-8")
        assert "sw-grill-docs" in content


def test_sw_grill_docs_requires_evidence_before_reporting_a_problem() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    checklist = CHECKLIST.read_text(encoding="utf-8")
    combined = f"{skill}\n{checklist}"

    assert "证据" in combined
    assert "仅凭术语缺失" in combined or "absence alone" in combined
    assert "引用" in combined


def test_sw_grill_docs_callers_wait_before_persisting_decisions() -> None:
    for path in CALLERS:
        content = path.read_text(encoding="utf-8")
        assert "用户确认后" in content
        assert "实时更新 CONTEXT.md" not in content
