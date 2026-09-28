from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-setup" / "SKILL.md"
REFERENCE = ROOT / "skills" / "sw-setup" / "references" / "package-lifecycle.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_setup_skill_declares_package_contract() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)

    assert frontmatter["metadata"]["version"] == "2.0.0"
    dependencies = frontmatter["metadata"]["external_dependencies"]
    assert {item["name"] for item in dependencies} == {
        "git",
        "package.py",
        "sw-knowledge-agent",
    }
    assert "## Input Contract" in content
    assert "## Output Contract" in content
    assert "## Acceptance Criteria" in content
    assert "## External Dependency Metadata" in content
    assert "## Agent Conversation Protocol" in content


def test_package_reference_covers_all_lifecycle_commands() -> None:
    content = REFERENCE.read_text(encoding="utf-8")
    for command in ("build", "publish", "download", "install", "init"):
        assert f"`{command}`" in content
    assert "packages/index.json" in content
    assert "latest" in content
    assert "checksum" in content
