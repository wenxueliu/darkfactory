from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-change-propagator" / "SKILL.md"
REFERENCE = ROOT / "skills" / "sw-change-propagator" / "references" / "change-propagation.md"


def test_change_skill_declares_contract_and_dependencies() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(content.split("---", 2)[1])

    assert frontmatter["metadata"]["version"] == "1.0.0"
    assert {item["name"] for item in frontmatter["metadata"]["external_dependencies"]} >= {
        "change.py",
        "PyYAML",
    }
    assert "## Input Contract" in content
    assert "## Output Contract" in content
    assert "## Acceptance Criteria" in content
    assert "small" in content
    assert "partial" in content
    assert "large" in content


def test_change_reference_defines_downstream_propagation() -> None:
    content = REFERENCE.read_text(encoding="utf-8")
    assert "design → decomposition → execution → merge → test → delivery" in content
    assert "source_revision" in content
    assert "target_revision" in content
    assert "superseded_by" in content
