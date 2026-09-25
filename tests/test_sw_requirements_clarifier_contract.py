from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-requirements-clarifier" / "SKILL.md"
GUIDE = ROOT / "skills" / "sw-requirements-clarifier" / "references" / "requirement-clarification.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_skill_declares_version_and_contract_sections() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)

    assert frontmatter["metadata"]["version"] == "2.1.0"
    assert "## Input Contract" in content
    assert "## Output Contract" in content
    assert "## Acceptance Criteria" in content


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


def test_requirement_clarifier_does_not_depend_on_external_commands() -> None:
    guide = GUIDE.read_text(encoding="utf-8")

    assert "scripts/kb-search.py" not in guide
    assert "cat CONTEXT.md" not in guide
    assert "强制委托 `sw-grill-docs`" not in guide
